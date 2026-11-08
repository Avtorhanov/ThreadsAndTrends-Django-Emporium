"""Заказ без аккаунта: ссылка, лимиты, идемпотентность, привязка к аккаунту, обезличивание."""

from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services import checkout as checkout_service
from orders.services import guest as guest_service
from orders.services import status as status_service
from orders.services.checkout import CheckoutInput
from store.models import ProductVariant
from store.services.cart import LineInput

pytestmark = pytest.mark.django_db

GUEST_API = "/api/v1/orders/guest/"
ORDER_API = "/api/v1/orders/guest/order/"
CLAIM_API = "/api/v1/orders/guest/claim/"
KEY = "k" * 32


def data(phone="+79001112233", **overrides) -> CheckoutInput:
    fields = {
        "delivery_method": DeliveryMethod.COURIER,
        "payment_method": PaymentMethod.AGREEMENT,
        "recipient_name": "Анна Гостева",
        "recipient_phone": phone,
        "delivery_address": "Москва, ул. Ленина, 1",
    }
    return CheckoutInput(**{**fields, **overrides})


def place(shirt, key=KEY, phone="+79001112233", **overrides):
    line = LineInput(shirt.variants.get(size="M").pk, 1)
    return checkout_service.guest_checkout(data(phone, **overrides), key, [line], consent=True)


def payload(shirt, **overrides) -> dict:
    return {
        "delivery_method": "courier",
        "payment_method": "agreement",
        "recipient_name": "Анна Гостева",
        "recipient_phone": "8 900 111-22-33",
        "delivery_address": "Москва, ул. Ленина, 1",
        "lines": [{"variant_id": shirt.variants.get(size="M").pk, "quantity": 1}],
        "consent": True,
        **overrides,
    }


@pytest.fixture
def anon():
    from rest_framework.test import APIClient

    return APIClient()


def test_creates_order_without_owner_and_reserves_stock(shirt):
    variant = shirt.variants.get(size="M")
    before = variant.stock
    result = place(shirt)
    variant.refresh_from_db()
    assert result.created and result.order.owner is None
    assert result.order.status == OrderStatus.AWAITING_AGREEMENT
    assert result.order.guest_consent_at is not None
    assert result.token not in result.order.guest_token_hash
    assert variant.stock == before - 1


def test_only_agreement_for_guest(shirt):
    with pytest.raises(ValidationError) as exc:
        place(shirt, payment_method=PaymentMethod.ON_DELIVERY)
    assert "payment_method" in exc.value.message_dict


def test_consent_required(shirt):
    line = LineInput(shirt.variants.get(size="M").pk, 1)
    with pytest.raises(ValidationError) as exc:
        checkout_service.guest_checkout(data(), KEY, [line], consent=False)
    assert "consent" in exc.value.message_dict


def test_short_key_rejected(shirt):
    with pytest.raises(ValidationError):
        place(shirt, key="short-key-1")


def test_replay_returns_same_order_and_link(shirt):
    first = place(shirt)
    second = place(shirt)
    assert not second.created
    assert second.order.pk == first.order.pk and second.token == first.token
    assert Order.objects.count() == 1


def test_replay_with_other_phone_gets_nothing(shirt):
    place(shirt)
    with pytest.raises(ValidationError):
        place(shirt, phone="+79005556677")
    assert Order.objects.count() == 1


def test_open_limit_by_phone(shirt):
    place(shirt, key="a" * 32)
    place(shirt, key="b" * 32)
    with pytest.raises(ValidationError) as exc:
        place(shirt, key="c" * 32)
    assert exc.value.code == "too_many_agreements"
    place(shirt, key="d" * 32, phone="+79005556677")


def test_limit_counts_account_orders(shirt, customer):
    from orders.tests.factories import make_order

    for _ in range(2):
        make_order(customer, status=OrderStatus.AWAITING_AGREEMENT, recipient_phone="+79001112233")
    with pytest.raises(ValidationError) as exc:
        place(shirt)
    assert exc.value.code == "too_many_agreements"


def test_no_customer_email_seller_notified(shirt, django_capture_on_commit_callbacks, settings):
    settings.SELLER_EMAIL = "seller@example.com"
    with django_capture_on_commit_callbacks(execute=True):
        result = place(shirt)
    assert [m.to for m in mail.outbox] == [["seller@example.com"]]
    assert result.order.status_changes.get().notified is False


# --- Доступ ---


def test_api_flow_and_foreign_token_404(anon, shirt):
    response = anon.post(GUEST_API, payload(shirt), format="json", HTTP_IDEMPOTENCY_KEY=KEY)
    assert response.status_code == 201
    token = response.data["access_token"]
    assert anon.get(ORDER_API, HTTP_X_ORDER_TOKEN=token).status_code == 200
    assert anon.get(ORDER_API, HTTP_X_ORDER_TOKEN="0" * 64).status_code == 404
    assert anon.get(ORDER_API).status_code == 404
    number = response.data["order"]["number"]
    assert anon.get(f"/api/v1/orders/{number}/").status_code == 401


def test_customer_cannot_open_guest_order_by_number(client_api, shirt):
    number = place(shirt).order.number
    assert client_api.get(f"/api/v1/orders/{number}/").status_code == 404


def test_link_lives_30_days_after_finish(anon, shirt):
    result = place(shirt)
    status_service.cancel(result.order, by=ChangedBy.CUSTOMER)
    order = Order.objects.get(pk=result.order.pk)
    assert order.guest_link_expires_at is not None
    assert anon.get(ORDER_API, HTTP_X_ORDER_TOKEN=result.token).status_code == 200
    Order.objects.filter(pk=order.pk).update(
        guest_link_expires_at=timezone.now() - timedelta(seconds=1)
    )
    assert anon.get(ORDER_API, HTTP_X_ORDER_TOKEN=result.token).status_code == 404


def test_cancel_by_token_returns_stock(anon, shirt):
    variant = shirt.variants.get(size="M")
    before = variant.stock
    result = place(shirt)
    response = anon.post(f"{ORDER_API}cancel/", HTTP_X_ORDER_TOKEN=result.token)
    assert response.status_code == 200 and response.data["status"] == OrderStatus.CANCELLED
    assert ProductVariant.objects.get(pk=variant.pk).stock == before


def test_rate_limit_by_ip(anon, shirt, settings):
    from orders.api.views import GuestCreateHourThrottle

    GuestCreateHourThrottle.THROTTLE_RATES = {
        **GuestCreateHourThrottle.THROTTLE_RATES,
        "order_create_guest": "1/hour",
    }
    try:
        first = anon.post(GUEST_API, payload(shirt), format="json", HTTP_IDEMPOTENCY_KEY=KEY)
        second = anon.post(GUEST_API, payload(shirt), format="json", HTTP_IDEMPOTENCY_KEY="z" * 32)
    finally:
        GuestCreateHourThrottle.THROTTLE_RATES = {
            **GuestCreateHourThrottle.THROTTLE_RATES,
            "order_create_guest": "5/hour",
        }
    assert first.status_code == 201 and second.status_code == 429


# --- Привязка и обезличивание ---


def test_claim_moves_order_and_kills_link(client_api, anon, customer, shirt):
    result = place(shirt)
    response = client_api.post(CLAIM_API, {"tokens": [result.token]}, format="json")
    assert response.status_code == 200 and response.data["numbers"] == [result.order.number]
    order = Order.objects.get(pk=result.order.pk)
    assert order.owner == customer and order.guest_token_hash == ""
    assert anon.get(ORDER_API, HTTP_X_ORDER_TOKEN=result.token).status_code == 404


def test_claim_requires_token_not_phone(customer, shirt):
    place(shirt)
    assert guest_service.claim(customer, ["0" * 64]) == []
    assert Order.objects.get().owner is None


def test_claim_ignores_expired_and_staff(customer, staff, shirt):
    result = place(shirt)
    assert guest_service.claim(staff, [result.token]) == []
    Order.objects.update(
        status=OrderStatus.CANCELLED, guest_link_expires_at=timezone.now() - timedelta(days=1)
    )
    assert guest_service.claim(customer, [result.token]) == []


def test_anonymize_after_retention(shirt):
    result = place(shirt)
    Order.objects.update(
        status=OrderStatus.DELIVERED,
        guest_link_expires_at=timezone.now()
        - (guest_service.RETENTION - guest_service.LINK_LIFETIME)
        - timedelta(hours=1),
    )
    assert guest_service.anonymize_old() == 1
    order = Order.objects.get(pk=result.order.pk)
    assert order.recipient_phone == "" and order.recipient_name == ""
    assert guest_service.anonymize_old() == 0


def test_recent_not_anonymized(shirt):
    result = place(shirt)
    status_service.cancel(result.order, by=ChangedBy.CUSTOMER)
    assert guest_service.anonymize_old() == 0


# --- Панель ---


def test_panel_shows_guest_order(admin_client, shirt):
    result = place(shirt)
    listing = admin_client.get("/api/v1/admin/orders/")
    assert listing.status_code == 200
    assert listing.data["results"][0]["customer"] is None
    detail = admin_client.get(f"/api/v1/admin/orders/{result.order.pk}/")
    assert detail.status_code == 200 and detail.data["customer"] is None


# --- Витрина ---


def test_web_guest_checkout_and_claim_on_login(client, customer, shirt):
    import re

    variant = shirt.variants.get(size="M")
    session = client.session
    session["cart"] = [[variant.pk, 1, None]]
    session.save()
    html = client.get(reverse("web:checkout")).content.decode()
    hidden = dict(re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', html))
    assert 'name="consent"' in html
    form = {
        "expected_total": hidden["expected_total"],
        "idempotency_key": hidden["idempotency_key"],
        "delivery_method": "courier",
        "payment_method": "agreement",
        "recipient_name": "Анна Гостева",
        "recipient_phone": "8 900 111-22-33",
        "delivery_address": "Москва, ул. Ленина, 1",
    }
    refused = client.post(reverse("web:checkout"), form)
    assert refused.status_code == 200 and not Order.objects.exists()
    response = client.post(reverse("web:checkout"), {**form, "consent": "on"})
    order = Order.objects.get()
    assert response.status_code == 302 and "/order/g/" in response["Location"]
    page = client.get(response["Location"])
    assert page.status_code == 200 and page["Referrer-Policy"] == "no-referrer"
    assert "cart" not in client.session

    login = client.post(
        reverse("web:login"), {"email": customer.email, "password": "Str0ng-Passw0rd!"}
    )
    assert login.status_code == 302
    order.refresh_from_db()
    assert order.owner == customer


def test_web_invalid_token_404(client):
    assert client.get(reverse("web:guest_order", args=["0" * 64])).status_code == 404
    assert client.post(reverse("web:guest_order_cancel", args=["x"])).status_code == 404


def test_opening_foreign_link_does_not_claim_on_login(client, customer, shirt):
    result = place(shirt)
    assert client.get(reverse("web:guest_order", args=[result.token])).status_code == 200
    client.post(reverse("web:login"), {"email": customer.email, "password": "Str0ng-Passw0rd!"})
    assert Order.objects.get().owner is None


def test_guest_order_size_limited(shirt):
    line = LineInput(shirt.variants.get(size="M").pk, checkout_service.MAX_GUEST_UNITS + 1)
    with pytest.raises(ValidationError) as exc:
        checkout_service.guest_checkout(data(), KEY, [line], consent=True)
    assert exc.value.code == "guest_order_too_big"


def test_replay_after_claim_makes_no_duplicate(customer, shirt):
    result = place(shirt)
    guest_service.claim(customer, [result.token])
    with pytest.raises(ValidationError):
        place(shirt)
    assert Order.objects.count() == 1
