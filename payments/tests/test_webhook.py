import pytest
from rest_framework.test import APIClient

from orders.models import OrderStatus, OrderStatusChange
from payments import services
from payments.models import Payment, PaymentStatus, Refund

pytestmark = pytest.mark.django_db

WEBHOOK = "/api/v1/payments/webhook/yookassa/"
YOOKASSA_IP = "185.71.76.10"


def notify(event, object_id, ip=YOOKASSA_IP, **extra):
    body = {"type": "notification", "event": event, "object": {"id": object_id, **extra}}
    return APIClient().post(WEBHOOK, body, format="json", REMOTE_ADDR=ip)


@pytest.fixture
def payment(online_order, fake_provider):
    return services.start_payment(online_order)


def test_webhook_marks_order_paid(payment, fake_provider, online_order):
    fake_provider.pay(payment.provider_payment_id)

    response = notify("payment.succeeded", payment.provider_payment_id)

    assert response.status_code == 200
    online_order.refresh_from_db()
    assert online_order.status == OrderStatus.PAID


def test_duplicate_webhook_does_not_change_state(payment, fake_provider, online_order):
    fake_provider.pay(payment.provider_payment_id)

    for _ in range(3):
        assert notify("payment.succeeded", payment.provider_payment_id).status_code == 200

    assert OrderStatusChange.objects.filter(order=online_order, to_status="paid").count() == 1
    assert Payment.objects.count() == 1
    assert Refund.objects.count() == 0


def test_body_is_not_trusted(payment, online_order):
    # Уведомление говорит «оплачен», но по API платёж ещё ждёт оплаты.
    response = notify(
        "payment.succeeded",
        payment.provider_payment_id,
        status="succeeded",
        paid=True,
        amount={"value": "3000.00", "currency": "RUB"},
    )

    assert response.status_code == 200
    online_order.refresh_from_db()
    assert online_order.status == OrderStatus.AWAITING_PAYMENT


def test_webhook_from_unknown_ip_is_rejected(payment, fake_provider, online_order):
    fake_provider.pay(payment.provider_payment_id)
    calls = len(fake_provider.calls)

    response = notify("payment.succeeded", payment.provider_payment_id, ip="203.0.113.7")

    assert response.status_code == 403
    assert len(fake_provider.calls) == calls  # провайдера даже не спрашивали
    online_order.refresh_from_db()
    assert online_order.status == OrderStatus.AWAITING_PAYMENT


def test_forwarded_for_is_ignored_without_trusted_proxy(payment, fake_provider):
    fake_provider.pay(payment.provider_payment_id)
    body = {"event": "payment.succeeded", "object": {"id": payment.provider_payment_id}}
    response = APIClient().post(
        WEBHOOK, body, format="json", REMOTE_ADDR="203.0.113.7", HTTP_X_FORWARDED_FOR=YOOKASSA_IP
    )
    assert response.status_code == 403


def test_forwarded_for_is_used_behind_proxy(payment, fake_provider, online_order, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    fake_provider.pay(payment.provider_payment_id)
    body = {"event": "payment.succeeded", "object": {"id": payment.provider_payment_id}}
    response = APIClient().post(
        WEBHOOK, body, format="json", REMOTE_ADDR="10.0.0.2", HTTP_X_FORWARDED_FOR=YOOKASSA_IP
    )
    assert response.status_code == 200
    online_order.refresh_from_db()
    assert online_order.status == OrderStatus.PAID


def test_unknown_payment_is_ignored(payment, fake_provider):
    response = notify("payment.succeeded", "pay-unknown")
    assert response.status_code == 200
    assert "get_payment" not in fake_provider.calls


def test_provider_down_asks_for_retry(payment, fake_provider, online_order):
    fake_provider.pay(payment.provider_payment_id)
    fake_provider.down = True

    assert notify("payment.succeeded", payment.provider_payment_id).status_code == 503

    fake_provider.down = False
    assert notify("payment.succeeded", payment.provider_payment_id).status_code == 200
    online_order.refresh_from_db()
    assert online_order.status == OrderStatus.PAID


def test_malformed_notification(payment):
    response = APIClient().post(
        WEBHOOK, {"event": "payment.succeeded"}, format="json", REMOTE_ADDR=YOOKASSA_IP
    )
    assert response.status_code == 400


def test_canceled_webhook(payment, fake_provider):
    fake_provider.decline(payment.provider_payment_id)
    assert notify("payment.canceled", payment.provider_payment_id).status_code == 200
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CANCELED


def test_refund_webhook_completes_refund(
    payment, fake_provider, online_order, customer, django_capture_on_commit_callbacks
):
    from orders.models import ChangedBy
    from orders.services import status as status_service

    fake_provider.pay(payment.provider_payment_id)
    services.sync_payment(payment)
    fake_provider.refund_status = "pending"
    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)
    fake_provider.refunds["ref-0001"]["status"] = "succeeded"

    assert notify("refund.succeeded", "ref-0001").status_code == 200

    assert Refund.objects.get().status == "succeeded"
    payment.refresh_from_db()
    assert payment.status == PaymentStatus.REFUNDED
