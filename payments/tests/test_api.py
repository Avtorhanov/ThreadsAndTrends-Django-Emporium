from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from orders.models import Order, OrderStatus
from orders.tests.factories import make_order
from payments import services
from payments.models import Payment, Refund, RefundStatus

pytestmark = pytest.mark.django_db

ORDERS = "/api/v1/orders/"
ADMIN_ORDERS = "/api/v1/admin/orders/"


def pay_url(order):
    return f"{ORDERS}{order.number}/pay/"


def refresh_url(order):
    return f"{ORDERS}{order.number}/pay/refresh/"


# --- Клиент ---


def test_payment_endpoints_require_authentication(online_order):
    client = APIClient()
    assert client.post(pay_url(online_order), {}, format="json").status_code == 401
    assert client.post(refresh_url(online_order)).status_code == 401


def test_pay_returns_confirmation_url(client_api, online_order, fake_provider):
    response = client_api.post(
        pay_url(online_order), {"return_url": "didishop://orders/x"}, format="json"
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["confirmation_url"].startswith("https://yoomoney.test/")
    assert body["payment_status"] == "pending"
    assert fake_provider.payments["pay-0001"]["return_url"] == "didishop://orders/x"


def test_pay_other_customers_order_is_404(online_order, other_customer, fake_provider):
    client = APIClient()
    client.force_authenticate(other_customer)
    assert client.post(pay_url(online_order), {}, format="json").status_code == 404
    assert client.post(refresh_url(online_order)).status_code == 404
    assert fake_provider.calls == []


def test_pay_rejects_foreign_return_url(client_api, online_order, fake_provider):
    response = client_api.post(
        pay_url(online_order), {"return_url": "https://evil.example/"}, format="json"
    )
    assert response.status_code == 400
    assert "return_url" in response.json()


def test_pay_not_payable_order(client_api, customer, fake_provider):
    order = make_order(customer)  # оплата при получении
    response = client_api.post(pay_url(order), {}, format="json")
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": ["Этот заказ оплачивается при получении."]}


def test_pay_when_provider_down_is_503(client_api, online_order, fake_provider):
    fake_provider.down = True
    assert client_api.post(pay_url(online_order), {}, format="json").status_code == 503


def test_refresh_after_return_marks_paid(client_api, online_order, fake_provider):
    client_api.post(pay_url(online_order), {}, format="json")
    fake_provider.pay("pay-0001")

    response = client_api.post(refresh_url(online_order))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert body["payment_status"] == "succeeded"
    assert body["can_pay"] is False and body["pay_until"] is None


def test_order_detail_payment_fields(client_api, online_order):
    body = client_api.get(f"{ORDERS}{online_order.number}/").json()

    assert body["can_pay"] is True
    assert body["pay_until"] is not None
    assert body["payment_status"] is None
    assert body["refund_status"] is None


def test_expired_order_cannot_be_paid(client_api, online_order, fake_provider):
    Order.objects.filter(pk=online_order.pk).update(created_at=timezone.now() - timedelta(hours=1))
    body = client_api.get(f"{ORDERS}{online_order.number}/").json()
    assert body["can_pay"] is False
    assert client_api.post(pay_url(online_order), {}, format="json").status_code == 400


def test_customer_cancel_of_paid_order_shows_refund(
    client_api, online_order, fake_provider, django_capture_on_commit_callbacks
):
    client_api.post(pay_url(online_order), {}, format="json")
    fake_provider.pay("pay-0001")
    client_api.post(refresh_url(online_order))

    with django_capture_on_commit_callbacks(execute=True):
        response = client_api.post(f"{ORDERS}{online_order.number}/cancel/")

    assert response.status_code == 200
    # Возврат выполняется после commit — свежий статус в карточке заказа.
    body = client_api.get(f"{ORDERS}{online_order.number}/").json()
    assert body["status"] == "cancelled"
    assert body["payment_status"] == "refunded"
    assert body["refund_status"] == "succeeded"


def test_checkout_with_online_payment(client_api, customer, fake_provider):
    from store.services import cart as cart_service
    from store.tests.factories import make_product

    cart_service.add(customer, make_product(price_kopecks=2_000_00).variants.get().pk, 1)
    response = client_api.post(
        ORDERS,
        {
            "delivery_method": "courier",
            "payment_method": "online",
            "recipient_name": "Иван Петров",
            "recipient_phone": "+79001234567",
            "delivery_address": "Москва, ул. Ленина, 1",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="key-online-0001",
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == "awaiting_payment"
    assert body["can_pay"] is True
    assert body["total_kopecks"] == 2_500_00


# --- Администратор ---


def test_admin_detail_shows_payments(admin_client, online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)
    services.sync_payment(payment)

    body = admin_client.get(f"{ADMIN_ORDERS}{online_order.pk}/").json()

    [item] = body["payments"]
    assert item["status"] == "succeeded"
    assert item["amount_kopecks"] == 3_000_00
    assert item["provider_payment_id"] == "pay-0001"
    assert item["refunds"] == []
    assert body["can_retry_refund"] is False


def test_admin_retry_refund(
    admin_client, online_order, staff, fake_provider, django_capture_on_commit_callbacks
):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)
    services.sync_payment(payment)
    fake_provider.refund_status = "canceled"
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            f"{ADMIN_ORDERS}{online_order.pk}/transition/", {"status": "cancelled"}, format="json"
        )
    assert response.status_code == 200
    body = admin_client.get(f"{ADMIN_ORDERS}{online_order.pk}/").json()
    assert body["can_retry_refund"] is True
    assert body["payments"][0]["refunds"][0]["status"] == "canceled"

    fake_provider.refund_status = "succeeded"
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(f"{ADMIN_ORDERS}{online_order.pk}/refund/")

    assert response.status_code == 200
    assert Refund.objects.filter(status=RefundStatus.SUCCEEDED).count() == 1
    assert admin_client.post(f"{ADMIN_ORDERS}{online_order.pk}/refund/").status_code == 400


def test_admin_payment_sync(admin_client, online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)

    response = admin_client.post(f"{ADMIN_ORDERS}{online_order.pk}/payment-sync/")

    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.PAID
    assert Payment.objects.get().status == "succeeded"


def test_admin_payment_actions_require_admin(online_order, customer, fake_provider):
    client = APIClient()
    client.force_login(customer)
    for action in ("refund", "payment-sync"):
        assert client.post(f"{ADMIN_ORDERS}{online_order.pk}/{action}/").status_code == 403
    assert APIClient().post(f"{ADMIN_ORDERS}{online_order.pk}/refund/").status_code == 401
