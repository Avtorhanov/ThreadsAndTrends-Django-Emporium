from dataclasses import replace
from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils import timezone

from orders.models import ChangedBy, Order, OrderStatus, OrderStatusChange
from orders.services import status as status_service
from orders.tests.factories import make_order
from payments import services
from payments.models import Payment, PaymentStatus, Refund, RefundReason, RefundStatus
from payments.providers import ProviderError

pytestmark = pytest.mark.django_db

S = OrderStatus


def paid_history(order):
    return OrderStatusChange.objects.filter(order=order, to_status=S.PAID).count()


def start_and_pay(order, fake):
    payment = services.start_payment(order)
    fake.pay(payment.provider_payment_id)
    return services.sync_payment(payment)


# --- Создание платежа ---


def test_start_payment_creates_provider_payment_with_receipt(online_order, fake_provider):
    payment = services.start_payment(online_order, return_url="exp://192.168.1.5:8081/--/orders/1")

    assert payment.status == PaymentStatus.PENDING
    assert payment.amount_kopecks == online_order.total_kopecks == 3_000_00
    assert payment.confirmation_url.startswith("https://yoomoney.test/")
    remote = fake_provider.payments[payment.provider_payment_id]
    assert remote["amount"] == 3_000_00
    assert remote["return_url"] == "exp://192.168.1.5:8081/--/orders/1"
    assert remote["metadata"]["order_number"] == online_order.number
    receipt = remote["receipt"]
    assert receipt["customer"] == {"email": "customer@example.com"}
    assert receipt["tax_system_code"] == 2
    [line] = receipt["items"]
    assert line["quantity"] == 2
    assert line["amount"] == {"value": "1500.00", "currency": "RUB"}
    assert line["vat_code"] == 1 and line["payment_subject"] == "commodity"
    assert "размер M" in line["description"]


def test_receipt_includes_delivery_and_sums_to_total(customer, fake_provider):
    order = make_order(customer, status=S.AWAITING_PAYMENT, payment_method="online")
    Order.objects.filter(pk=order.pk).update(
        delivery_kopecks=500_00, total_kopecks=F("items_total_kopecks") + 500_00
    )
    order.refresh_from_db()

    payment = services.start_payment(order)

    items = fake_provider.payments[payment.provider_payment_id]["receipt"]["items"]
    assert items[-1]["description"] == "Доставка" and items[-1]["payment_subject"] == "service"
    total = sum(int(i["amount"]["value"].replace(".", "")) * i["quantity"] for i in items)
    assert total == order.total_kopecks


def test_receipts_can_be_disabled(online_order, fake_provider, settings):
    settings.PAYMENTS_RECEIPTS_ENABLED = False
    payment = services.start_payment(online_order)
    assert fake_provider.payments[payment.provider_payment_id]["receipt"] is None


def test_repeated_start_reuses_pending_payment(online_order, fake_provider):
    first = services.start_payment(online_order)
    second = services.start_payment(online_order)

    assert first.pk == second.pk
    assert fake_provider.calls == ["create_payment"]
    assert Payment.objects.count() == 1


@pytest.mark.parametrize(
    ("status", "payment_method"),
    [
        (S.CONFIRMED, "on_delivery"),
        (S.PAID, "online"),
        (S.CANCELLED, "online"),
    ],
)
def test_start_payment_rejects_not_payable_orders(
    customer, fake_provider, status, payment_method
):
    order = make_order(customer, status=status, payment_method=payment_method)
    with pytest.raises(ValidationError) as exc:
        services.start_payment(order)
    assert exc.value.error_list[0].code == "not_payable"
    assert fake_provider.calls == []


def test_start_payment_after_deadline_is_rejected(online_order, fake_provider):
    Order.objects.filter(pk=online_order.pk).update(
        created_at=timezone.now() - timedelta(minutes=31)
    )
    online_order.refresh_from_db()
    assert services.can_pay(online_order) is False
    with pytest.raises(ValidationError):
        services.start_payment(online_order)


def test_return_url_must_point_to_app(online_order, fake_provider):
    with pytest.raises(ValidationError) as exc:
        services.start_payment(online_order, return_url="https://evil.example/phish")
    assert "return_url" in exc.value.message_dict
    assert Payment.objects.count() == 0


def test_default_return_url(online_order, fake_provider):
    payment = services.start_payment(online_order)
    remote = fake_provider.payments[payment.provider_payment_id]
    assert remote["return_url"] == f"didishop://orders/{online_order.number}"


def test_transient_error_keeps_attempt_and_retry_uses_same_key(online_order, fake_provider):
    fake_provider.fail_next = ProviderError("timeout", transient=True)
    with pytest.raises(services.PaymentUnavailable):
        services.start_payment(online_order)
    payment = Payment.objects.get()
    assert payment.status == PaymentStatus.PENDING and payment.provider_payment_id is None

    retried = services.start_payment(online_order)

    assert retried.pk == payment.pk
    assert retried.provider_payment_id == "pay-0001"
    assert len(fake_provider.payments) == 1


def test_rejected_payment_is_marked_canceled(online_order, fake_provider):
    fake_provider.fail_next = ProviderError("bad receipt", transient=False, status_code=400)
    with pytest.raises(ValidationError) as exc:
        services.start_payment(online_order)
    assert exc.value.error_list[0].code == "payment_rejected"
    assert Payment.objects.get().status == PaymentStatus.CANCELED
    # Новая попытка возможна.
    assert services.start_payment(online_order).status == PaymentStatus.PENDING


# --- Сверка платежа ---


def test_succeeded_payment_marks_order_paid(
    online_order, fake_provider, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        payment = start_and_pay(online_order, fake_provider)

    online_order.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCEEDED and payment.paid_at is not None
    assert online_order.status == S.PAID
    change = online_order.status_changes.get(to_status=S.PAID)
    assert change.changed_by == ChangedBy.SYSTEM
    assert any("оплачен" in m.subject for m in mail.outbox)


def test_repeated_sync_does_not_change_state(online_order, fake_provider):
    payment = start_and_pay(online_order, fake_provider)
    services.sync_payment(payment)
    services.sync_payment(payment)

    assert paid_history(online_order) == 1
    assert Payment.objects.get().status == PaymentStatus.SUCCEEDED
    assert Refund.objects.count() == 0


def test_pending_payment_changes_nothing(online_order, fake_provider):
    payment = services.start_payment(online_order)
    services.sync_payment(payment)

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT
    assert Payment.objects.get().status == PaymentStatus.PENDING


def test_declined_payment_allows_new_attempt(online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.decline(payment.provider_payment_id)
    services.sync_payment(payment)

    payment.refresh_from_db()
    online_order.refresh_from_db()
    assert payment.status == PaymentStatus.CANCELED
    assert payment.cancellation_reason == "insufficient_funds"
    assert online_order.status == S.AWAITING_PAYMENT

    second = services.start_payment(online_order)
    assert second.pk != payment.pk and second.provider_payment_id == "pay-0002"


def test_wrong_amount_does_not_pay_order_and_is_refunded(
    online_order, fake_provider, django_capture_on_commit_callbacks
):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id, amount_kopecks=1_00)

    with django_capture_on_commit_callbacks(execute=True):
        services.sync_payment(payment)

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT
    refund = Refund.objects.get()
    assert refund.reason == RefundReason.AMOUNT_MISMATCH
    assert refund.amount_kopecks == 1_00  # возвращается фактически списанное
    assert refund.status == RefundStatus.SUCCEEDED
    assert fake_provider.refunds["ref-0001"]["receipt"] is None


def test_wrong_currency_does_not_pay_order(online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id, currency="USD")
    services.sync_payment(payment)

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT
    assert Refund.objects.get().reason == RefundReason.AMOUNT_MISMATCH


def test_provider_returning_other_id_is_ignored(online_order, fake_provider):
    payment = services.start_payment(online_order)
    remote = fake_provider.get_payment(payment.provider_payment_id)
    forged = replace(remote, id="pay-9999", status="succeeded")

    services._apply_payment(payment.pk, forged)

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT
    assert Payment.objects.get().provider_payment_id == payment.provider_payment_id


# --- Возвраты ---


def test_payment_after_cancellation_is_refunded(
    online_order, fake_provider, django_capture_on_commit_callbacks
):
    payment = services.start_payment(online_order)
    status_service.cancel(online_order, by=ChangedBy.SYSTEM)  # автоотмена
    fake_provider.pay(payment.provider_payment_id)  # покупатель успел заплатить

    with django_capture_on_commit_callbacks(execute=True):
        services.sync_payment(payment)

    online_order.refresh_from_db()
    payment.refresh_from_db()
    assert online_order.status == S.CANCELLED
    refund = Refund.objects.get()
    assert refund.reason == RefundReason.LATE_PAYMENT
    assert refund.status == RefundStatus.SUCCEEDED
    assert payment.status == PaymentStatus.REFUNDED
    assert fake_provider.refunds["ref-0001"]["amount"] == online_order.total_kopecks
    assert any("возвращены" in m.subject for m in mail.outbox)


def test_cancel_after_payment_refunds_money(
    online_order, customer, fake_provider, django_capture_on_commit_callbacks
):
    payment = start_and_pay(online_order, fake_provider)

    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)

    payment.refresh_from_db()
    refund = Refund.objects.get()
    assert refund.reason == RefundReason.ORDER_CANCELLED
    assert refund.status == RefundStatus.SUCCEEDED
    assert refund.provider_refund_id == "ref-0001"
    assert payment.status == PaymentStatus.REFUNDED
    assert fake_provider.refunds["ref-0001"]["payment_id"] == payment.provider_payment_id
    assert fake_provider.refunds["ref-0001"]["receipt"]["items"]


def test_admin_cancel_of_assembled_paid_order_refunds(
    online_order, staff, fake_provider, django_capture_on_commit_callbacks
):
    start_and_pay(online_order, fake_provider)
    status_service.transition(online_order, S.ASSEMBLED, by=ChangedBy.ADMIN, actor=staff)

    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.ADMIN, actor=staff)

    assert Refund.objects.get().status == RefundStatus.SUCCEEDED


def test_cancel_unpaid_online_order_creates_no_refund(online_order, customer, fake_provider):
    services.start_payment(online_order)
    status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)
    assert Refund.objects.count() == 0


def test_refund_after_network_error_is_retried_once(
    online_order, customer, fake_provider, django_capture_on_commit_callbacks
):
    start_and_pay(online_order, fake_provider)
    fake_provider.down = True
    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)
    refund = Refund.objects.get()
    assert refund.status == RefundStatus.PENDING

    fake_provider.down = False
    services.execute_refund(refund.pk)
    services.execute_refund(refund.pk)

    refund.refresh_from_db()
    assert refund.status == RefundStatus.SUCCEEDED
    assert len(fake_provider.refunds) == 1


def test_pending_refund_is_completed_by_sync(
    online_order, customer, fake_provider, django_capture_on_commit_callbacks
):
    start_and_pay(online_order, fake_provider)
    fake_provider.refund_status = "pending"
    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)
    refund = Refund.objects.get()
    assert refund.status == RefundStatus.PENDING and refund.provider_refund_id == "ref-0001"

    fake_provider.refunds["ref-0001"]["status"] = "succeeded"
    services.sync_refund(refund)

    refund.refresh_from_db()
    assert refund.status == RefundStatus.SUCCEEDED
    assert Payment.objects.get().status == PaymentStatus.REFUNDED


def test_declined_refund_can_be_retried_by_admin(
    online_order, customer, fake_provider, django_capture_on_commit_callbacks
):
    payment = start_and_pay(online_order, fake_provider)
    fake_provider.refund_status = "canceled"
    with django_capture_on_commit_callbacks(execute=True):
        status_service.cancel(online_order, by=ChangedBy.CUSTOMER, actor=customer)
    assert Refund.objects.get().status == RefundStatus.CANCELED
    online_order.refresh_from_db()
    assert services.refund_retry_payment(online_order).pk == payment.pk

    fake_provider.refund_status = "succeeded"
    with django_capture_on_commit_callbacks(execute=True):
        services.retry_refund(online_order)

    assert list(Refund.objects.values_list("status", flat=True)) == [
        RefundStatus.CANCELED,
        RefundStatus.SUCCEEDED,
    ]
    assert services.refund_retry_payment(online_order) is None
    with pytest.raises(ValidationError):
        services.retry_refund(online_order)


def test_second_succeeded_payment_is_refunded_as_duplicate(
    online_order, fake_provider, django_capture_on_commit_callbacks
):
    first = services.start_payment(online_order)
    fake_provider.decline(first.provider_payment_id)
    services.sync_payment(first)
    second = start_and_pay(online_order, fake_provider)
    # Провайдер «передумал» по первой попытке — моделируем повторное списание.
    Payment.objects.filter(pk=first.pk).update(status=PaymentStatus.PENDING)
    fake_provider.pay(first.provider_payment_id)

    with django_capture_on_commit_callbacks(execute=True):
        services.sync_payment(first)

    online_order.refresh_from_db()
    assert online_order.status == S.PAID
    assert Refund.objects.get().payment_id == first.pk
    assert Refund.objects.get().reason == RefundReason.DUPLICATE_PAYMENT
    assert Payment.objects.get(pk=second.pk).status == PaymentStatus.SUCCEEDED


# --- Сводка для экрана заказа ---


def test_summary(online_order, fake_provider):
    order = Order.objects.prefetch_related("payments__refunds").get(pk=online_order.pk)
    info = services.summary(order)
    assert info.can_pay is True
    assert info.pay_until == online_order.created_at + timedelta(minutes=30)
    assert info.payment_status is None and info.refund_status is None

    start_and_pay(online_order, fake_provider)
    order = Order.objects.prefetch_related("payments__refunds").get(pk=online_order.pk)
    info = services.summary(order)
    assert info.can_pay is False and info.pay_until is None
    assert info.payment_status == PaymentStatus.SUCCEEDED
