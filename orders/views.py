# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from orders.models import Order
from orders.utils import validate_checkout_data, create_order, create_order_with_items
from store.models import CartItem, Cart


@login_required
def checkout(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    total_price = cart_item.product.price * cart_item.quantity

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')
        size = request.POST.get('size')
        # payment_method = request.POST.get('payment_method')
        username = request.user.username

        validation_result = validate_checkout_data(full_name, username)
        if not validation_result['valid']:
            messages.error(request, validation_result['message'])
            return redirect('checkout', item_id=item_id)

        order = create_order(request.user, total_price, address, phone_number, full_name, cart_item, size)
        messages.success(request, 'Заказ оформлен!')
        return redirect('order_detail', order_id=order.id)

    return render(request, 'orders/checkout.html', {'cart_item': cart_item, 'total_price': total_price})


def checkout_all(request):
    cart = Cart.objects.get(owner=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

        username = request.user.username

        validation_result = validate_checkout_data(full_name, username)
        if not validation_result['valid']:
            messages.error(request, validation_result['message'])
            return redirect('checkout_all')

        # Создаем заказ, включающий все товары из корзины
        order = create_order_with_items(request.user, address, phone_number, full_name, cart_items, total_price)

        # Очищаем корзину после оформления заказа
        cart_items.delete()

        messages.success(request, 'Заказ оформлен!')
        # Перенаправляем на страницу деталей заказа
        return redirect(reverse('order_detail', kwargs={'order_id': order.id}))

    return render(request, 'orders/checkout_all.html', {'cart_items': cart_items, 'total_price': total_price})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user)
    order_items = order.orderitem_set.all()
    return render(request, 'orders/order_detail.html', {'order': order, 'order_items': order_items})

@login_required
def my_orders(request):
    orders = Order.objects.filter(owner=request.user, is_ordered=True).order_by('-date_ordered')
    return render(request, 'orders/my_orders.html', {'orders': orders})

@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user)
    order.delete()
    messages.success(request, 'Заказ удален!')
    return HttpResponseRedirect(reverse('my_orders'))
