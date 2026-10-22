"""Оформление, оплата и «Мои заказы» на витрине. Логика — orders.services и payments.services.

Чужой заказ — 404 (выборка только среди заказов покупателя). Оформление идемпотентно: ключ
попытки — скрытое поле формы, повторный сабмит (двойной клик, «Назад» + отправка) возвращает
уже созданный заказ.
"""

import logging
import uuid

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from orders.models import ChangedBy, DeliveryMethod, Order, OrderItem, PaymentMethod
from orders.services import checkout as checkout_service
from orders.services import status as status_service
from payments import services as payments
from payments.models import Payment, PaymentStatus
from store.models import ProductImage

from .. import ratelimit
from ..forms import CheckoutForm
from .account import _apply_errors
from .common import customer_required, flash_errors

logger = logging.getLogger(__name__)

PAYMENT_UNAVAILABLE = "Платёжный сервис временно недоступен. Попробуйте через минуту."
ORDERS_PAGE_SIZE = 20


def _customer_orders(user):
    return Order.objects.filter(owner=user)


def _detail_queryset(user):
    return _customer_orders(user).prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related("product").prefetch_related(
                Prefetch("product__images", queryset=ProductImage.objects.order_by("position"))
            ),
        ),
        "status_changes",
        Prefetch("payments", queryset=Payment.objects.prefetch_related("refunds")),
    )


# --- Оформление ---


@customer_required
def checkout(request):
    preview = checkout_service.preview(request.user)
    if not preview.cart.lines:
        messages.info(request, "Корзина пуста.")
        return redirect("web:cart")
    if not preview.cart.can_checkout:
        messages.error(request, "Проверьте корзину: некоторые товары недоступны.")
        return redirect("web:cart")

    items_total = preview.cart.total_kopecks
    options = {option.method: option for option in preview.delivery_options}
    form = CheckoutForm(
        request.POST or None,
        delivery_methods=list(options),
        payment_methods=preview.payment_methods,
        initial={
            "delivery_method": DeliveryMethod.COURIER,
            "payment_method": preview.payment_methods[0],
            "recipient_name": preview.defaults.recipient_name
            or request.user.get_full_name().strip(),
            "recipient_phone": preview.defaults.recipient_phone,
            "delivery_address": preview.defaults.delivery_address,
            "expected_total": items_total,
            "idempotency_key": uuid.uuid4().hex,
        },
    )

    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        if not ratelimit.allow(request, "order_create", user=request.user):
            form.add_error(None, ratelimit.TOO_MANY)
        else:
            # Покупатель видел сумму товаров expected_total и цену доставки рядом со способом —
            # итог для сверки считается так же, как на странице.
            seen_items = data["expected_total"]
            expected = seen_items + checkout_service.delivery_cost(
                data["delivery_method"], seen_items
            )
            try:
                order, _ = checkout_service.checkout(
                    request.user,
                    checkout_service.CheckoutInput(
                        delivery_method=data["delivery_method"],
                        payment_method=data["payment_method"],
                        recipient_name=data["recipient_name"],
                        recipient_phone=data["recipient_phone"],
                        delivery_address=data["delivery_address"],
                        comment=data["comment"],
                        expected_total_kopecks=expected,
                    ),
                    data["idempotency_key"],
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                if order.payment_method == PaymentMethod.ONLINE and payments.can_pay(order):
                    return _start_payment(request, order)
                messages.success(request, f"Заказ {order.number} оформлен.")
                return redirect("web:order", number=order.number)

    return render(
        request,
        "web/orders/checkout.html",
        {
            "form": form,
            "cart": preview.cart,
            "items_total": items_total,
            "options": preview.delivery_options,
            "free_from": preview.free_delivery_from_kopecks,
            "pickup": options.get(DeliveryMethod.PICKUP),
            "tab": "cart",
            "noindex": True,
        },
    )


# --- Оплата ---


def _return_url(request, order: Order) -> str:
    # Адрес того же сайта, на котором покупатель (основной домен или прежний): cookie сессии
    # привязана к домену. Префиксы всех адресов разрешены в PAYMENTS_RETURN_URL_PREFIXES.
    return request.build_absolute_uri(reverse("web:order", args=[order.number])) + "?paid=1"


def _start_payment(request, order: Order):
    try:
        payment = payments.start_payment(order, return_url=_return_url(request, order))
    except payments.PaymentUnavailable:
        messages.error(request, PAYMENT_UNAVAILABLE)
        return redirect("web:order", number=order.number)
    except ValidationError as exc:
        flash_errors(request, exc)
        return redirect("web:order", number=order.number)
    # Страница оплаты ЮKassa; оттуда покупатель вернётся на страницу заказа (?paid=1).
    return redirect(payment.confirmation_url)


@customer_required
@require_POST
def pay(request, number: str):
    order = get_object_or_404(_customer_orders(request.user), number=number)
    if not ratelimit.allow(request, "payment_start", user=request.user):
        messages.error(request, ratelimit.TOO_MANY)
        return redirect("web:order", number=order.number)
    return _start_payment(request, order)


def _sync_payment(request, order: Order) -> None:
    """Сверка незавершённой оплаты с ЮKassa: после возврата со страницы оплаты и при открытии
    заказа, ожидающего оплаты. Статус меняется только по ответу API провайдера."""
    if not ratelimit.allow(request, "payment_refresh", user=request.user):
        return
    try:
        payments.sync_order_payments(order)
    except payments.PaymentUnavailable:
        messages.warning(request, "Не удалось проверить оплату. Обновите страницу через минуту.")


# --- Мои заказы ---


@customer_required
def order_list(request):
    orders = (
        _customer_orders(request.user)
        .annotate(items_count=Sum("items__quantity"))
        .order_by("-created_at", "-id")
    )
    page = Paginator(orders, ORDERS_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "web/orders/list.html",
        {"page": page, "orders": page.object_list, "tab": "profile", "noindex": True},
    )


@customer_required
def order_detail(request, number: str):
    order = get_object_or_404(_customer_orders(request.user), number=number)
    # Как экран заказа в приложении: незавершённая оплата сверяется при открытии.
    pending = order.payments.filter(status=PaymentStatus.PENDING).exclude(provider_payment_id=None)
    if order.payment_method == PaymentMethod.ONLINE and pending.exists():
        _sync_payment(request, order)
    order = get_object_or_404(_detail_queryset(request.user), pk=order.pk)
    payment = payments.summary(order)
    return render(
        request,
        "web/orders/detail.html",
        {
            "order": order,
            "items": list(order.items.all()),
            "history": list(order.status_changes.all()),
            "payment": payment,
            "can_cancel": status_service.can_cancel(order, ChangedBy.CUSTOMER),
            "returned": request.GET.get("paid") == "1",
            "tab": "profile",
            "noindex": True,
        },
    )


@customer_required
@require_POST
def order_cancel(request, number: str):
    order = get_object_or_404(_customer_orders(request.user), number=number)
    try:
        status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=request.user)
    except ValidationError as exc:
        flash_errors(request, exc)
    else:
        messages.success(request, f"Заказ {order.number} отменён.")
    return redirect("web:order", number=order.number)
