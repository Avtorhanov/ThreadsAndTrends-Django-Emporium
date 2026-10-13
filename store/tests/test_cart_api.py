import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.throttling import SimpleRateThrottle

from store.models import CartItem
from store.services import cart as cart_service
from store.services import catalog

from .conftest import image_file
from .factories import make_product

pytestmark = pytest.mark.django_db

CART = "/api/v1/cart/"
ITEMS = "/api/v1/cart/items/"
MERGE = "/api/v1/cart/merge/"
QUOTE = "/api/v1/cart/quote/"
ACK = "/api/v1/cart/ack-prices/"


def item_url(pk):
    return f"{ITEMS}{pk}/"


@pytest.fixture
def client_api(api_client, customer):
    api_client.force_authenticate(customer)
    return api_client


@pytest.fixture
def shirt():
    product = make_product(name="Футболка", price_kopecks=1_500_00, stock=5, sizes=("S", "M"))
    catalog.add_product_image(product, image_file())
    return product


def test_cart_requires_authentication(api_client):
    for method, url in [
        ("get", CART),
        ("post", ITEMS),
        ("patch", item_url(1)),
        ("delete", item_url(1)),
        ("post", MERGE),
        ("post", ACK),
    ]:
        assert getattr(api_client, method)(url, {}, format="json").status_code == 401


def test_add_and_read_cart(client_api, shirt):
    variant = shirt.variants.get(size="M")

    response = client_api.post(ITEMS, {"variant_id": variant.pk, "quantity": 2}, format="json")

    assert response.status_code == 201
    item = CartItem.objects.get()
    body = client_api.get(CART).json()
    assert body == response.json()
    assert body["total_kopecks"] == 3_000_00
    assert body["items_count"] == 2
    assert body["can_checkout"] is True
    assert body["has_problems"] is False
    assert body["has_price_changes"] is False
    [line] = body["items"]
    assert line["product"]["cover_url"].startswith("http://testserver/")
    assert {key: value for key, value in line.items() if key != "product"} == {
        "id": item.pk,
        "variant_id": variant.pk,
        "size": "M",
        "quantity": 2,
        "status": "ok",
        "max_quantity": 5,
        "unit_price_kopecks": 1_500_00,
        "seen_price_kopecks": 1_500_00,
        "price_changed": False,
        "line_total_kopecks": 3_000_00,
    }
    assert line["product"]["slug"] == shirt.slug
    assert line["product"]["name"] == "Футболка"
    # Точный остаток не раскрывается сверх лимита покупки.
    assert "stock" not in line


def test_empty_cart(client_api):
    body = client_api.get(CART).json()
    assert body == {
        "items": [],
        "total_kopecks": 0,
        "items_count": 0,
        "can_checkout": False,
        "has_problems": False,
        "has_price_changes": False,
    }


def test_add_errors_are_400_with_message(client_api, shirt):
    variant = shirt.variants.get(size="S")

    response = client_api.post(ITEMS, {"variant_id": variant.pk, "quantity": 6}, format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Можно добавить не больше 5 шт."]}

    response = client_api.post(ITEMS, {"variant_id": 999_999}, format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Товар недоступен для заказа."]}

    response = client_api.post(ITEMS, {"variant_id": variant.pk, "quantity": 0}, format="json")
    assert response.status_code == 400
    assert "quantity" in response.json()


def test_set_quantity_via_patch_body(client_api, customer, shirt):
    summary = cart_service.add(customer, shirt.variants.get(size="S").pk)
    url = item_url(summary.lines[0].id)

    response = client_api.patch(url, {"quantity": 4}, format="json")
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4

    assert client_api.patch(url, {"quantity": 6}, format="json").status_code == 400
    assert client_api.patch(url, {"quantity": 0}, format="json").status_code == 400
    assert client_api.patch(url, {}, format="json").status_code == 400


def test_foreign_cart_item_returns_404(client_api, staff, shirt):
    other_item = cart_service.add(staff, shirt.variants.get(size="S").pk).lines[0].id

    assert client_api.patch(item_url(other_item), {"quantity": 2}, format="json").status_code == 404
    assert client_api.delete(item_url(other_item)).status_code == 404
    assert CartItem.objects.get(pk=other_item).quantity == 1


def test_delete_item(client_api, customer, shirt):
    summary = cart_service.add(customer, shirt.variants.get(size="S").pk)
    response = client_api.delete(item_url(summary.lines[0].id))
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_removed_product_is_marked_unavailable(client_api, customer, shirt):
    cart_service.add(customer, shirt.variants.get(size="S").pk, 2)
    catalog.soft_delete_product(shirt)

    body = client_api.get(CART).json()

    [line] = body["items"]
    assert (line["status"], line["max_quantity"], line["line_total_kopecks"]) == (
        "unavailable",
        0,
        0,
    )
    assert line["product"]["name"] == "Футболка"
    assert (body["total_kopecks"], body["can_checkout"], body["has_problems"]) == (0, False, True)


def test_price_change_warning_and_ack(client_api, customer, shirt):
    cart_service.add(customer, shirt.variants.get(size="S").pk)
    shirt.price_kopecks = 1_990_00
    shirt.save()

    body = client_api.get(CART).json()
    assert body["has_price_changes"] is True
    assert body["items"][0]["seen_price_kopecks"] == 1_500_00
    assert body["total_kopecks"] == 1_990_00

    body = client_api.post(ACK).json()
    assert body["has_price_changes"] is False


def test_merge(client_api, shirt):
    hidden = make_product(is_active=False)
    response = client_api.post(
        MERGE,
        {
            "items": [
                {"variant_id": shirt.variants.get(size="S").pk, "quantity": 9},
                {"variant_id": hidden.variants.get().pk, "quantity": 1, "seen_price_kopecks": 1},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert [line["quantity"] for line in body["cart"]["items"]] == [5]
    assert body["notices"] == [
        {"variant_id": shirt.variants.get(size="S").pk, "reason": "quantity_limited"},
        {"variant_id": hidden.variants.get().pk, "reason": "unavailable"},
    ]


def test_quote_is_public_and_ignores_bad_token(api_client, shirt):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired-or-garbage")
    variant = shirt.variants.get(size="M")

    response = api_client.post(
        QUOTE,
        {"items": [{"variant_id": variant.pk, "quantity": 2, "seen_price_kopecks": 1_000_00}]},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    [line] = body["items"]
    assert (line["id"], line["status"], line["price_changed"]) == (None, "ok", True)
    assert body["total_kopecks"] == 3_000_00
    assert not CartItem.objects.exists()


def test_quote_unknown_variant_has_no_product(api_client):
    body = api_client.post(
        QUOTE, {"items": [{"variant_id": 999_999, "quantity": 1}]}, format="json"
    ).json()
    [line] = body["items"]
    assert (line["status"], line["product"], line["size"], line["unit_price_kopecks"]) == (
        "unavailable",
        None,
        None,
        None,
    )


def test_quote_validates_input(api_client, settings):
    assert api_client.post(QUOTE, {}, format="json").status_code == 400
    bad = {"items": [{"variant_id": 1, "quantity": 0}]}
    assert api_client.post(QUOTE, bad, format="json").status_code == 400
    too_many = {"items": [{"variant_id": n, "quantity": 1} for n in range(1, 52)]}
    assert api_client.post(QUOTE, too_many, format="json").status_code == 400


def test_quote_is_throttled(api_client, monkeypatch):
    rates = {**SimpleRateThrottle.THROTTLE_RATES, "cart_quote": "2/min"}
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
    body = {"items": []}

    assert api_client.post(QUOTE, body, format="json").status_code == 200
    assert api_client.post(QUOTE, body, format="json").status_code == 200
    assert api_client.post(QUOTE, body, format="json").status_code == 429


def test_cart_query_count_does_not_grow_with_items(client_api, customer):
    def queries_for_cart():
        with CaptureQueriesContext(connection) as ctx:
            assert client_api.get(CART).status_code == 200
        return len(ctx.captured_queries)

    product = make_product()
    catalog.add_product_image(product, image_file())
    cart_service.add(customer, product.variants.get().pk)
    one = queries_for_cart()

    for _ in range(5):
        product = make_product(sizes=("S", "M"))
        catalog.add_product_image(product, image_file())
        cart_service.add(customer, product.variants.get(size="M").pk)
    assert queries_for_cart() == one
    # позиции + варианты с товарами + изображения
    assert one <= 3
