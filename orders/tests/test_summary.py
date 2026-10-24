from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from orders.models import Order, OrderStatus, PaymentMethod
from store.tests.factories import make_product

from .factories import make_order

pytestmark = pytest.mark.django_db

SUMMARY = "/api/v1/admin/summary/"


def aged(order: Order, days: int) -> Order:
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=days))
    return order


def test_summary_requires_admin_session(customer, client_api):
    assert APIClient().get(SUMMARY).status_code == 401
    assert client_api.get(SUMMARY).status_code in (401, 403)
    non_staff = APIClient()
    non_staff.force_login(customer)
    assert non_staff.get(SUMMARY).status_code == 403


def test_summary_empty_shop(admin_client):
    data = admin_client.get(SUMMARY).json()
    assert data["today"] == {"orders": 0, "turnover_kopecks": 0}
    assert data["last_30_days"] == {"orders": 0, "turnover_kopecks": 0}
    assert data["awaiting_payment"] == data["to_assemble"] == data["to_deliver"] == 0
    assert data["low_stock_count"] == 0
    assert data["low_stock"] == []


def test_summary_counts_and_turnover(admin_client, customer, settings):
    settings.ADMIN_LOW_STOCK_THRESHOLD = 2
    product = make_product(name="Футболка", price_kopecks=1_000_00, stock=10)
    make_order(customer, product, status=OrderStatus.CONFIRMED)  # сегодня, собрать
    make_order(customer, product, status=OrderStatus.PAID, payment_method=PaymentMethod.ONLINE)
    make_order(
        customer,
        product,
        status=OrderStatus.AWAITING_PAYMENT,
        payment_method=PaymentMethod.ONLINE,
    )  # не в обороте, но в числе заказов
    make_order(customer, product, status=OrderStatus.CANCELLED)  # отменённый не учитывается
    aged(make_order(customer, product, status=OrderStatus.SHIPPED), days=3)
    aged(make_order(customer, product, status=OrderStatus.DELIVERED, quantity=2), days=20)
    aged(make_order(customer, product, status=OrderStatus.DELIVERED), days=45)  # вне периодов

    data = admin_client.get(SUMMARY).json()

    assert data["today"] == {"orders": 3, "turnover_kopecks": 2_000_00}
    assert data["last_7_days"] == {"orders": 4, "turnover_kopecks": 3_000_00}
    assert data["last_30_days"] == {"orders": 5, "turnover_kopecks": 5_000_00}
    assert data["awaiting_payment"] == 1
    assert data["to_assemble"] == 2
    assert data["to_deliver"] == 1


def test_summary_low_stock(admin_client, settings):
    settings.ADMIN_LOW_STOCK_THRESHOLD = 3
    shirt = make_product(name="Футболка", stock=2, sizes=("S", "M"))
    shirt.variants.filter(size="M").update(stock=0)
    make_product(name="Кепка", stock=3)
    make_product(name="Худи", stock=4)  # выше порога
    make_product(name="Скрытый", stock=0, is_active=False)
    deleted = make_product(name="Удалённый", stock=0)
    deleted.deleted_at = timezone.now()
    deleted.save()
    removed_variant = make_product(name="Шарф", stock=0).variants.get()
    removed_variant.deleted_at = timezone.now()
    removed_variant.save()

    data = admin_client.get(SUMMARY).json()

    assert data["low_stock_threshold"] == 3
    assert data["low_stock_count"] == 3
    assert [(row["product_name"], row["size"], row["stock"]) for row in data["low_stock"]] == [
        ("Футболка", "M", 0),
        ("Футболка", "S", 2),
        ("Кепка", "", 3),
    ]
    assert data["low_stock"][0]["product_id"] == shirt.pk
