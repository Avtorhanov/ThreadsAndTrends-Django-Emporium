# -*- coding: utf-8 -*-
from orders.models import Order, OrderItem
from django.db import models, transaction

# оформление заказа
def validate_checkout_data(full_name, username):
    if full_name != username:
        return {'valid': False, 'message': 'Пожалуйста, введите ваше имя правильно.'}
    return {'valid': True}

def create_order(user, total_price, address, phone_number, full_name, cart_item, size):
    # Получаем максимальный номер заказа для данного пользователя
    max_user_order_number = Order.objects.filter(owner=user).aggregate(models.Max('user_order_number'))['user_order_number__max']
    # Если у пользователя уже есть заказы, увеличиваем номер на 1, иначе начинаем с 1
    new_user_order_number = max_user_order_number + 1 if max_user_order_number is not None else 1

    order_number = f"{new_user_order_number}"

    order = Order.objects.create(
        owner=user,
        order_number=order_number,
        total_price=total_price,
        address=address,
        phone_number=phone_number,
        full_name=full_name,
        is_ordered=True,
        size=size,
        # payment_method=payment_method
    )

    # Создаем связанный объект OrderItem
    OrderItem.objects.create(
        order=order,
        product=cart_item.product,
        quantity=cart_item.quantity,
        price=cart_item.product.price,
        description=cart_item.product.description
    )

    # Удаляем товар из корзины
    cart_item.delete()

    return order


@transaction.atomic
def create_order_with_items(user, address, phone_number, full_name, cart_items, total_price):
    # Получаем максимальный номер заказа для данного пользователя
    max_user_order_number = Order.objects.filter(owner=user).aggregate(models.Max('user_order_number'))['user_order_number__max']
    # Если у пользователя уже есть заказы, увеличиваем номер на 1, иначе начинаем с 1
    new_user_order_number = max_user_order_number + 1 if max_user_order_number is not None else 1

    order_number = f"{new_user_order_number}"

    # Создаем заказ
    order = Order.objects.create(
        owner=user,
        order_number=order_number,
        address=address,
        phone_number=phone_number,
        total_price=total_price,
        full_name=full_name,
        is_ordered=True
    )

    # Создаем связанный объект OrderItem для каждого товара в корзине
    for cart_item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            quantity=cart_item.quantity,
            price=cart_item.product.price,
            description=cart_item.product.description
        )

    return order