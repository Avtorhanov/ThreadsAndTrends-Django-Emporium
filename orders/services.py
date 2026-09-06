from decimal import Decimal

from django.db import transaction

from orders.models import Order, OrderItem


@transaction.atomic
def create_order_from_cart_items(
    *,
    user,
    cart_items,
    full_name,
    address,
    phone_number,
    size=None,
):
    cart_items = list(cart_items)

    if not cart_items:
        raise ValueError("Невозможно создать заказ без товаров.")

    total_price = sum(
        (
            item.price * item.quantity
            for item in cart_items
        ),
        Decimal("0.00"),
    )

    order = Order.objects.create(
        owner=user,
        total_price=total_price,
        address=address,
        phone_number=phone_number,
        full_name=full_name,
        is_ordered=True,
        size=size or "",
    )

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.price,
            description=item.product.description,
        )
        for item in cart_items
    ])

    for item in cart_items:
        item.delete()

    return order