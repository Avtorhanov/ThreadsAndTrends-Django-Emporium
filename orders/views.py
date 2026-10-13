"""Легаси-страницы заказов (только суперпользователь, см. LOGIN_URL). Оформление заказа
удалено в сессии 4; новое оформление и заказы — API сессии 5."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order


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
        "orders/order_detail.html",
        {
            "order": order,
            "order_items": order_items,
        },
    )


@login_required
def my_orders(request):
    orders = Order.objects.filter(
        owner=request.user,
        is_ordered=True,
    ).order_by("-date_ordered")

    return render(
        request,
        "orders/my_orders.html",
        {"orders": orders},
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
        "Заказ удален!",
    )

    return redirect("my_orders")
