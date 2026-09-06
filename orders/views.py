# -*- coding: utf-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from orders.models import Order
from orders.forms import CheckoutForm
from orders.services import create_order_from_cart_items
from store.models import CartItem, Cart


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__owner=request.user,
    )

    total_price = (
        cart_item.product.price * cart_item.quantity
    )

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            order = create_order_from_cart_items(
                user=request.user,
                cart_items=[cart_item],
                **form.cleaned_data,
            )

            messages.success(
                request,
                "Заказ оформлен!",
            )

            return redirect(
                "order_detail",
                order_id=order.id,
            )
    else:
        form = CheckoutForm()

    return render(
        request,
        "orders/checkout.html",
        {
            "cart_item": cart_item,
            "total_price": total_price,
            "form": form,
        },
    )

@login_required
@require_http_methods(["GET", "POST"])
def checkout_all(request):
    cart = get_object_or_404(
        Cart,
        owner=request.user,
    )

    cart_items = CartItem.objects.filter(cart=cart)

    total_price = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    if request.method == "POST":
        form = CheckoutForm(request.POST)

        if form.is_valid():
            order = create_order_from_cart_items(
                user=request.user,
                cart_items=cart_items,
                **form.cleaned_data,
            )

            messages.success(
                request,
                "Заказ оформлен!",
            )

            return redirect(
                "order_detail",
                order_id=order.id,
            )
    else:
        form = CheckoutForm()

    return render(
        request,
        "orders/checkout_all.html",
        {
            "cart_items": cart_items,
            "total_price": total_price,
            "form": form,
        },
    )


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        owner=request.user,
    )

    order_items = order.orderitem_set.all()

    return render(
        request,
        'orders/order_detail.html',
        {
            'order': order,
            'order_items': order_items,
        },
    )


@login_required
def my_orders(request):
    orders = (
        Order.objects
        .filter(
            owner=request.user,
            is_ordered=True,
        )
        .order_by('-date_ordered')
    )

    return render(
        request,
        'orders/my_orders.html',
        {'orders': orders},
    )


@login_required
@require_POST
def delete_order(request, order_id):
    order = get_object_or_404(
        Order,
        id=order_id,
        owner=request.user,
    )

    order.delete()

    messages.success(
        request,
        'Заказ удален!',
    )

    return redirect('my_orders')