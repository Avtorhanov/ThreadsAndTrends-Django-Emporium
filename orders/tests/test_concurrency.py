"""Параллельные оформления на настоящих транзакциях Postgres (каждый поток — своё соединение)."""

import threading

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection

from orders.models import DeliveryMethod, Order, PaymentMethod
from orders.services import checkout as checkout_service
from orders.services.checkout import CheckoutInput
from store.models import ProductVariant
from store.services import cart as cart_service
from store.tests.factories import make_product

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)

INPUT = CheckoutInput(
    delivery_method=DeliveryMethod.COURIER,
    payment_method=PaymentMethod.ON_DELIVERY,
    recipient_name="Иван Петров",
    recipient_phone="+79001234567",
    delivery_address="Москва, ул. Ленина, 1",
)


def run_parallel(calls):
    """Запускает вызовы одновременно; возвращает результаты или исключения."""
    barrier = threading.Barrier(len(calls))
    results: list = [None] * len(calls)

    def worker(index, call):
        try:
            barrier.wait()
            results[index] = call()
        except Exception as exc:  # noqa: BLE001 — результат проверяет тест
            results[index] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_last_item_is_sold_once():
    variant = make_product(stock=1).variants.get()
    buyers = [User.objects.create_user(email=f"b{i}@example.com", password="p") for i in range(2)]
    for buyer in buyers:
        cart_service.add(buyer, variant.pk, 1)

    results = run_parallel(
        [
            lambda buyer=buyer: checkout_service.checkout(buyer, INPUT, f"key-buyer-{buyer.pk}")
            for buyer in buyers
        ]
    )

    orders = [r for r in results if isinstance(r, tuple)]
    errors = [r for r in results if isinstance(r, ValidationError)]
    assert len(orders) == 1 and len(errors) == 1, results
    assert errors[0].error_list[0].code == "cart_changed"
    assert ProductVariant.all_objects.get(pk=variant.pk).stock == 0
    assert Order.objects.count() == 1


def test_double_submit_with_same_key_creates_one_order():
    variant = make_product(stock=5).variants.get()
    buyer = User.objects.create_user(email="b@example.com", password="p")
    cart_service.add(buyer, variant.pk, 2)

    results = run_parallel(
        [lambda: checkout_service.checkout(buyer, INPUT, "key-same-0001") for _ in range(2)]
    )

    assert all(isinstance(r, tuple) for r in results), results
    assert {order.pk for order, _ in results} == {Order.objects.get().pk}
    assert sorted(created for _, created in results) == [False, True]
    assert ProductVariant.all_objects.get(pk=variant.pk).stock == 3
