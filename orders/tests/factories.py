"""Фабрики заказов для тестов (orders, store, accounts). Заказ создаётся напрямую,
без checkout, — для проверки истории, доступа и удаления аккаунта."""

from itertools import count

from orders.models import (
    ChangedBy,
    DeliveryMethod,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusChange,
    PaymentMethod,
)
from store.tests.factories import make_product

_seq = count(1)


def make_order(
    owner,
    product=None,
    *,
    status=OrderStatus.CONFIRMED,
    quantity=1,
    payment_method=PaymentMethod.ON_DELIVERY,
    delivery_method=DeliveryMethod.COURIER,
    **fields,
) -> Order:
    n = next(_seq)
    product = product or make_product()
    variant = product.variants.first()
    items_total = product.price_kopecks * quantity
    fields.setdefault("recipient_name", "Иван Петров")
    fields.setdefault("recipient_phone", "+79001234567")
    fields.setdefault("delivery_address", "Москва, ул. Ленина, 1, кв. 1")
    order = Order.objects.create(
        owner=owner,
        number=f"T-{n}",
        status=status,
        payment_method=payment_method,
        delivery_method=delivery_method,
        items_total_kopecks=items_total,
        delivery_kopecks=0,
        total_kopecks=items_total,
        idempotency_key=f"test-key-{n:04d}",
        **fields,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        variant=variant,
        product_name=product.name,
        size=variant.size,
        sku=variant.sku,
        price_kopecks=product.price_kopecks,
        quantity=quantity,
    )
    OrderStatusChange.objects.create(
        order=order, from_status="", to_status=status, changed_by=ChangedBy.CUSTOMER, actor=owner
    )
    return order
