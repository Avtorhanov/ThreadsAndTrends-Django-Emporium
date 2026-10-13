"""Гонки на настоящих транзакциях Postgres (каждый поток — своё соединение)."""

import pytest
from django.contrib.auth import get_user_model

from orders.models import OrderStatus, PaymentMethod
from orders.tests.factories import make_order
from orders.tests.test_concurrency import run_parallel
from payments import services
from payments.models import Payment, Refund

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def order():
    buyer = User.objects.create_user(email="buyer@example.com", password="p")
    return make_order(
        buyer, status=OrderStatus.AWAITING_PAYMENT, payment_method=PaymentMethod.ONLINE
    )


def test_parallel_pay_clicks_create_one_payment(order, fake_provider):
    results = run_parallel([lambda: services.start_payment(order) for _ in range(3)])

    assert all(isinstance(r, Payment) for r in results), results
    assert Payment.objects.count() == 1
    assert len(fake_provider.payments) == 1
    assert {r.confirmation_url for r in results} == {Payment.objects.get().confirmation_url}


def test_parallel_webhooks_mark_paid_once(order, fake_provider):
    payment = services.start_payment(order)
    fake_provider.pay(payment.provider_payment_id)

    results = run_parallel([lambda: services.sync_payment(payment) for _ in range(3)])

    assert all(isinstance(r, Payment) for r in results), results
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
    assert order.status_changes.filter(to_status=OrderStatus.PAID).count() == 1
    assert Refund.objects.count() == 0


def test_payment_racing_autocancel_is_paid_or_refunded(order, fake_provider):
    payment = services.start_payment(order)
    fake_provider.pay(payment.provider_payment_id)

    results = run_parallel(
        [lambda: services.sync_payment(payment), lambda: services.cancel_awaiting_payment(order)]
    )

    order.refresh_from_db()
    payment.refresh_from_db()
    if order.status == OrderStatus.CANCELLED:
        # Отмена успела раньше — деньги возвращаются (поздняя оплата или отмена оплаченного).
        assert Refund.objects.count() == 1, results
    else:
        assert order.status == OrderStatus.PAID, results
        assert Refund.objects.count() == 0
