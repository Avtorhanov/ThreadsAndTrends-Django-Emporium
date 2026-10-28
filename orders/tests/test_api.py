import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from orders.models import DeliveryMethod, Order, OrderStatus
from store.models import ProductVariant
from store.services import cart as cart_service

from .factories import make_order

pytestmark = pytest.mark.django_db

ORDERS = "/api/v1/orders/"
CHECKOUT = "/api/v1/orders/checkout/"
ADMIN_ORDERS = "/api/v1/admin/orders/"

PAYLOAD = {
    "delivery_method": "courier",
    "payment_method": "on_delivery",
    "recipient_name": "Иван Петров",
    "recipient_phone": "+7 900 123-45-67",
    "delivery_address": "Москва, ул. Ленина, 1, кв. 2",
}


def create(client, key="key-00000001", **overrides):
    return client.post(ORDERS, {**PAYLOAD, **overrides}, format="json", HTTP_IDEMPOTENCY_KEY=key)


def detail_url(number):
    return f"{ORDERS}{number}/"


# --- Клиент ---


def test_orders_require_authentication(customer):
    order = make_order(customer)
    client = APIClient()
    for method, url in [
        ("get", ORDERS),
        ("post", ORDERS),
        ("get", CHECKOUT),
        ("get", detail_url(order.number)),
        ("post", f"{detail_url(order.number)}cancel/"),
    ]:
        assert getattr(client, method)(url, {}, format="json").status_code == 401


def test_checkout_preview(client_api, filled_cart):
    body = client_api.get(CHECKOUT).json()

    assert body["cart"]["total_kopecks"] == 3_700_00
    assert body["cart"]["can_checkout"] is True
    assert [(o["method"], o["cost_kopecks"]) for o in body["delivery_options"]] == [
        ("courier", 500_00),
        ("pickup", 0),
    ]
    assert body["payment_methods"] == ["online", "on_delivery"]
    assert body["free_delivery_from_kopecks"] == 10_000_00
    assert body["defaults"] == {"recipient_name": "", "recipient_phone": "", "delivery_address": ""}


def test_create_order_and_repeat_with_same_key(client_api, filled_cart):
    response = create(client_api, expected_total_kopecks=4_200_00)

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["status_display"] == "Принят"
    assert body["total_kopecks"] == 4_200_00
    assert body["recipient_phone"] == "+79001234567"
    assert body["can_cancel"] is True
    assert {item["product_name"] for item in body["items"]} == {"Футболка", "Кепка"}
    assert [h["to_status"] for h in body["status_history"]] == ["confirmed"]
    assert client_api.get("/api/v1/cart/").json()["items"] == []

    repeat = create(client_api, expected_total_kopecks=4_200_00)
    assert repeat.status_code == 200
    assert repeat.json()["number"] == body["number"]
    assert Order.objects.count() == 1


def test_create_requires_idempotency_key(client_api, filled_cart):
    response = client_api.post(ORDERS, PAYLOAD, format="json")
    assert response.status_code == 400
    assert "Idempotency-Key" in response.json()["non_field_errors"][0]


def test_create_validation_errors_are_per_field(client_api, filled_cart):
    response = create(client_api, recipient_phone="123", delivery_address="")
    assert response.status_code == 400
    assert set(response.json()) == {"recipient_phone", "delivery_address"}


def test_create_with_empty_cart_is_400(client_api):
    response = create(client_api)
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Корзина пуста."]}


def test_list_and_detail_show_only_own_orders(client_api, customer, other_customer):
    own = make_order(customer, quantity=3)
    foreign = make_order(other_customer)

    body = client_api.get(ORDERS).json()
    assert [row["number"] for row in body["results"]] == [own.number]
    assert body["results"][0]["items_count"] == 3

    assert client_api.get(detail_url(own.number)).status_code == 200
    assert client_api.get(detail_url(foreign.number)).status_code == 404
    assert client_api.post(f"{detail_url(foreign.number)}cancel/").status_code == 404
    foreign.refresh_from_db()
    assert foreign.status == OrderStatus.CONFIRMED


def test_customer_cancels_order(client_api, customer):
    order = make_order(customer, quantity=2)
    variant = order.items.get().variant
    before = variant.stock

    response = client_api.post(f"{detail_url(order.number)}cancel/")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["can_cancel"] is False
    assert ProductVariant.all_objects.get(pk=variant.pk).stock == before + 2


def test_customer_cannot_cancel_shipped(client_api, customer):
    order = make_order(customer, status=OrderStatus.SHIPPED)
    assert client_api.get(detail_url(order.number)).json()["can_cancel"] is False
    response = client_api.post(f"{detail_url(order.number)}cancel/")
    assert response.status_code == 400


def test_order_list_has_constant_queries(client_api, customer):
    make_order(customer)
    with CaptureQueriesContext(connection) as one:
        client_api.get(ORDERS)
    for _ in range(4):
        make_order(customer)
    with CaptureQueriesContext(connection) as many:
        assert len(client_api.get(ORDERS).json()["results"]) == 5
    assert len(many) == len(one)


def test_order_detail_has_constant_queries(client_api, customer, shirt, cap):
    small = make_order(customer)
    with CaptureQueriesContext(connection) as one:
        client_api.get(detail_url(small.number))

    for product in (shirt, cap):
        cart_service.add(customer, product.variants.first().pk, 1)
    number = create(client_api).json()["number"]
    with CaptureQueriesContext(connection) as two:
        assert len(client_api.get(detail_url(number)).json()["items"]) == 2
    assert len(two) == len(one)


# --- Администратор ---


def test_admin_orders_require_admin_session(customer, client_api, staff):
    order = make_order(customer)
    assert APIClient().get(ADMIN_ORDERS).status_code == 401
    # JWT/аутентификация клиента панель не пускает.
    assert client_api.get(ADMIN_ORDERS).status_code in (401, 403)
    non_staff = APIClient()
    non_staff.force_login(customer)
    assert non_staff.get(ADMIN_ORDERS).status_code == 403
    assert (
        non_staff.post(f"{ADMIN_ORDERS}{order.pk}/transition/", {"status": "assembled"}).status_code
        == 403
    )


def test_admin_list_filters_and_search(admin_client, customer, other_customer):
    courier = make_order(customer, recipient_phone="+79161112233")
    pickup = make_order(
        other_customer, status=OrderStatus.ASSEMBLED, delivery_method=DeliveryMethod.PICKUP
    )
    done = make_order(customer, status=OrderStatus.DELIVERED)

    def numbers(query=""):
        response = admin_client.get(f"{ADMIN_ORDERS}{query}")
        assert response.status_code == 200, response.content
        return {row["number"] for row in response.json()["results"]}

    assert numbers() == {courier.number, pickup.number, done.number}
    assert numbers("?status=assembled") == {pickup.number}
    assert numbers("?delivery_method=pickup") == {pickup.number}
    assert numbers("?unfinished=true") == {courier.number, pickup.number}
    assert numbers("?search=other@") == {pickup.number}
    assert numbers("?search=8 916 111-22-33") == {courier.number}
    assert numbers(f"?search={done.number}") == {done.number}
    assert admin_client.get(f"{ADMIN_ORDERS}?created_from=13.10.2026").status_code == 400

    row = admin_client.get(f"{ADMIN_ORDERS}?status=assembled").json()["results"][0]
    assert row["customer"]["email"] == "other@example.com"


def test_admin_transition_flow(admin_client, customer, staff):
    order = make_order(customer)
    url = f"{ADMIN_ORDERS}{order.pk}/"

    detail = admin_client.get(url).json()
    assert [t["status"] for t in detail["allowed_transitions"]] == ["assembled", "cancelled"]

    response = admin_client.post(f"{url}transition/", {"status": "assembled"}, format="json")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["status"] == "assembled"
    assert [t["status"] for t in body["allowed_transitions"]] == ["shipped", "cancelled"]
    assert body["status_history"][-1]["actor_email"] == staff.email
    assert body["status_history"][-1]["changed_by"] == "admin"

    response = admin_client.post(f"{url}transition/", {"status": "delivered"}, format="json")
    assert response.status_code == 400
    assert "Нельзя перевести" in response.json()["non_field_errors"][0]

    response = admin_client.post(f"{url}transition/", {"status": "paid"}, format="json")
    assert response.status_code == 400


def test_buy_now_preview_and_create(client_api, customer, filled_cart, cap):
    variant = cap.variants.get()
    body = client_api.get(CHECKOUT, {"variant": variant.pk, "quantity": 2}).json()
    assert [(i["variant_id"], i["quantity"]) for i in body["cart"]["items"]] == [(variant.pk, 2)]

    response = create(
        client_api,
        key="buy-now-api-01",
        buy_now={"variant_id": variant.pk, "quantity": 2},
        expected_total_kopecks=body["cart"]["total_kopecks"] + 500_00,
    )
    assert response.status_code == 201
    assert [(i["product_name"], i["quantity"]) for i in response.json()["items"]] == [("Кепка", 2)]
    # Корзина (футболка и кепка) не изменилась.
    assert len(client_api.get("/api/v1/cart/").json()["items"]) == 2


def test_buy_now_preview_validates_params(client_api):
    assert client_api.get(CHECKOUT, {"variant": "abc"}).status_code == 400


def test_admin_transition_with_comment_visible_to_customer(admin_client, client_api, customer):
    order = make_order(customer)
    body = {"status": "assembled", "comment": "Заменили пакет на коробку", "notify": False}
    response = admin_client.post(f"{ADMIN_ORDERS}{order.pk}/transition/", body, format="json")
    assert response.status_code == 200, response.content
    last = response.json()["status_history"][-1]
    assert (last["comment"], last["notified"]) == ("Заменили пакет на коробку", False)

    history = client_api.get(detail_url(order.number)).json()["status_history"]
    assert history[-1]["comment"] == "Заменили пакет на коробку"
    assert "notified" not in history[-1]
