from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from orders.models import ChangedBy, Order, OrderStatus
from orders.tests.factories import make_order
from payments import services, tasks
from payments.models import Payment, PaymentStatus, Refund, RefundReason
from store.models import ProductVariant

pytestmark = pytest.mark.django_db

S = OrderStatus


def age(model, obj, minutes):
    model.objects.filter(pk=obj.pk).update(created_at=timezone.now() - timedelta(minutes=minutes))
    obj.refresh_from_db()


def stock(order):
    return ProductVariant.all_objects.get(pk=order.items.get().variant_id).stock


def test_periodic_tasks_registered():
    paths = {entry["task"] for entry in settings.PERIODIC_TASKS}
    assert {"payments.tasks.sync_pending", "payments.tasks.cancel_unpaid_orders"} <= paths


def test_unpaid_order_is_cancelled_after_timeout(online_order, fake_provider):
    services.start_payment(online_order)
    fresh = make_order(online_order.owner, status=S.AWAITING_PAYMENT, payment_method="online")
    age(Order, online_order, 31)
    before = stock(online_order)

    tasks.cancel_unpaid_orders.enqueue()

    online_order.refresh_from_db()
    fresh.refresh_from_db()
    assert online_order.status == S.CANCELLED
    assert online_order.status_changes.last().changed_by == ChangedBy.SYSTEM
    assert stock(online_order) == before + 2
    assert fresh.status == S.AWAITING_PAYMENT
    assert Refund.objects.count() == 0


def test_paid_order_is_not_cancelled(online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)  # webhook потерян
    age(Order, online_order, 31)

    tasks.cancel_unpaid_orders.enqueue()

    online_order.refresh_from_db()
    assert online_order.status == S.PAID
    assert Refund.objects.count() == 0


def test_autocancel_waits_when_provider_down(online_order, fake_provider):
    services.start_payment(online_order)
    age(Order, online_order, 31)
    fake_provider.down = True

    tasks.cancel_unpaid_orders.enqueue()

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT


def test_autocancel_of_order_without_payment_attempt(online_order, fake_provider):
    age(Order, online_order, 31)
    tasks.cancel_unpaid_orders.enqueue()
    online_order.refresh_from_db()
    assert online_order.status == S.CANCELLED
    assert fake_provider.calls == []


def test_on_delivery_orders_are_not_touched(customer, fake_provider):
    order = make_order(customer, status=S.CONFIRMED)
    age(Order, order, 120)
    tasks.cancel_unpaid_orders.enqueue()
    order.refresh_from_db()
    assert order.status == S.CONFIRMED


def test_sync_pending_applies_lost_webhook(online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)
    age(Payment, payment, 2)

    tasks.sync_pending.enqueue()

    online_order.refresh_from_db()
    assert online_order.status == S.PAID


def test_sync_pending_skips_fresh_payments(online_order, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)

    tasks.sync_pending.enqueue()

    online_order.refresh_from_db()
    assert online_order.status == S.AWAITING_PAYMENT


def test_sync_pending_cancels_never_created_attempt(online_order, fake_provider):
    payment = Payment.objects.create(
        order=online_order, amount_kopecks=online_order.total_kopecks, idempotency_key="k" * 32
    )
    age(Payment, payment, 11)

    tasks.sync_pending.enqueue()

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.CANCELED
    assert payment.cancellation_reason == "not_created"


def test_sync_pending_retries_refund(online_order, customer, fake_provider):
    payment = services.start_payment(online_order)
    fake_provider.pay(payment.provider_payment_id)
    services.sync_payment(payment)
    refund = Refund.objects.create(
        payment=payment,
        amount_kopecks=payment.amount_kopecks,
        reason=RefundReason.ORDER_CANCELLED,
        idempotency_key="r" * 32,
    )
    age(Refund, refund, 2)

    tasks.sync_pending.enqueue()

    refund.refresh_from_db()
    assert refund.status == "succeeded"


def test_provider_down_does_not_break_sync(online_order, fake_provider):
    payment = services.start_payment(online_order)
    age(Payment, payment, 2)
    fake_provider.down = True

    tasks.sync_pending.enqueue()  # не падает

    payment.refresh_from_db()
    assert payment.status == PaymentStatus.PENDING
