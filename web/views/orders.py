"""Оформление, оплата и «Мои заказы» на витрине. Логика — orders.services и payments.services.

Чужой заказ — 404 (выборка только среди заказов покупателя). Оформление идемпотентно: ключ
попытки — скрытое поле формы, повторный сабмит (двойной клик, «Назад» + отправка) возвращает
уже созданный заказ.
"""

import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from orders.models import ChangedBy, DeliveryMethod, Order, OrderItem, PaymentMethod
from orders.services import agreement as agreement_service
from orders.services import checkout as checkout_service
from orders.services import guest
from orders.services import status as status_service
from payments import services as payments
from payments.models import Payment, PaymentStatus
from store.models import ProductImage, ProductVariant
from store.services.cart import LineInput

from .. import cart as web_cart
from .. import guest_links, ratelimit
from ..forms import CheckoutForm
from .account import _apply_errors
from .common import customer_required, flash_errors, shopper_required

logger = logging.getLogger(__name__)

# Кнопка связи с продавцом у заказа «по согласованию»: подпись и значок канала (свои значки,
# не фирменные логотипы — как на «Контактах»).
AGREEMENT_BUTTONS = {
    "whatsapp": ("Написать в WhatsApp", "chat"),
    "telegram": ("Написать в Telegram", "send"),
    "vk": ("Написать ВКонтакте", "people"),
    "phone": ("Позвонить продавцу", "phone"),
}
PAYMENT_UNAVAILABLE = "Платёжный сервис временно недоступен. Попробуйте через минуту."
ORDERS_PAGE_SIZE = 20


def _customer_orders(user):
    return Order.objects.filter(owner=user)


def _detail_queryset(user):
    return _detail_queryset_of(_customer_orders(user))


def _detail_queryset_of(queryset):
    return queryset.prefetch_related(
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


def buy_now_line(request) -> LineInput | None:
    """«Купить сейчас»: ?variant=<id>&qty=<n> в адресе оформления (и при отправке формы)."""
    raw_variant, raw_qty = request.GET.get("variant", ""), request.GET.get("qty", "1")
    if not raw_variant:
        return None
    if not (raw_variant.isdigit() and raw_qty.isdigit()):
        raise Http404("Неверный товар.")
    quantity = min(max(int(raw_qty), 1), settings.CART_MAX_QUANTITY)
    return LineInput(int(raw_variant), quantity)


def _back_to_product(buy_now: LineInput):
    variant = ProductVariant.objects.select_related("product").filter(pk=buy_now.variant_id).first()
    if variant is None:
        return redirect("web:home")
    return redirect("web:product", slug=variant.product.slug)


def _guest_limit_ok(request, phone: str) -> bool:
    # Те же области и ключи, что у POST /api/v1/orders/guest/.
    return (
        ratelimit.allow(request, "order_create_guest")
        and ratelimit.allow(request, "order_create_guest_day")
        and ratelimit.allow(request, "order_create_guest_phone", phone=phone)
    )


def _input_from(data: dict, expected: int) -> checkout_service.CheckoutInput:
    return checkout_service.CheckoutInput(
        delivery_method=data["delivery_method"],
        payment_method=data["payment_method"],
        recipient_name=data["recipient_name"],
        recipient_phone=data["recipient_phone"],
        delivery_address=data["delivery_address"],
        comment=data["comment"],
        expected_total_kopecks=expected,
    )


def _submit_guest(request, form, buy_now, lines):
    """Оформление без аккаунта: редирект на заказ или None с ошибками в форме."""
    data = form.cleaned_data
    try:
        phone = checkout_service.normalize_phone(data["recipient_phone"])
    except ValidationError:
        phone = None  # опечатка в номере не тратит попытки: ошибку покажет сервис
    if phone is not None and not _guest_limit_ok(request, phone):
        form.add_error(None, ratelimit.TOO_MANY)
        return None
    seen_items = data["expected_total"]
    expected = seen_items + checkout_service.delivery_cost(data["delivery_method"], seen_items)
    try:
        result = checkout_service.guest_checkout(
            _input_from(data, expected),
            data["idempotency_key"],
            lines,
            consent=data["consent"],
            buy_now=buy_now is not None,
        )
    except ValidationError as exc:
        _apply_errors(form, exc)
        return None
    guest_links.remember(request, result.token)
    if result.created and buy_now is None:
        web_cart.take_guest_lines(request)
    messages.success(
        request, f"Заказ {result.order.number} создан — напишите продавцу, чтобы его согласовать."
    )
    return redirect("web:guest_order", token=result.token)


@shopper_required
def checkout(request):
    buy_now = buy_now_line(request)
    is_guest = not request.user.is_authenticated
    guest_lines = ([buy_now] if buy_now else web_cart.guest_lines(request)) if is_guest else []
    if is_guest:
        preview = checkout_service.guest_preview(guest_lines)
        if not preview.payment_methods:
            login_url = reverse("web:login")
            messages.info(request, "Чтобы оформить заказ этим способом, войдите в аккаунт.")
            return redirect(f"{login_url}?{urlencode({'next': request.get_full_path()})}")
    else:
        preview = checkout_service.preview(request.user, buy_now)
    if buy_now is not None and not preview.cart.can_checkout:
        line = preview.cart.lines[0]
        reason = "закончился" if line.status == "out_of_stock" else "недоступен для заказа"
        if line.status == "exceeds_stock":
            reason = f"есть только {line.max_quantity} шт."
        messages.error(request, f"Товар {reason}.")
        return _back_to_product(buy_now)
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
        guest=is_guest,
        initial={
            "delivery_method": DeliveryMethod.COURIER,
            "payment_method": preview.payment_methods[0],
            "recipient_name": preview.defaults.recipient_name
            or ("" if is_guest else request.user.get_full_name().strip()),
            "recipient_phone": preview.defaults.recipient_phone,
            "delivery_address": preview.defaults.delivery_address,
            "expected_total": items_total,
            "idempotency_key": uuid.uuid4().hex,
        },
    )

    if request.method == "POST" and form.is_valid() and is_guest:
        response = _submit_guest(request, form, buy_now, guest_lines)
        if response is not None:
            return response
    elif request.method == "POST" and form.is_valid():
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
                    _input_from(data, expected),
                    data["idempotency_key"],
                    buy_now=buy_now,
                )
            except ValidationError as exc:
                _apply_errors(form, exc)
            else:
                if order.payment_method == PaymentMethod.ONLINE and payments.can_pay(order):
                    return _start_payment(request, order)
                if order.payment_method == PaymentMethod.AGREEMENT:
                    messages.success(
                        request,
                        f"Заказ {order.number} создан — напишите продавцу, чтобы его согласовать.",
                    )
                else:
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
            "buy_now": buy_now,
            "is_guest": is_guest,
            "action": request.get_full_path(),
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


def _order_context(request, order: Order) -> dict:
    payment = payments.summary(order)
    base = settings.SITE_URL or request.build_absolute_uri("/").rstrip("/")
    agreement = agreement_service.link(order, base)
    label, icon = AGREEMENT_BUTTONS.get(agreement.kind, ("", "")) if agreement else ("", "")
    return {
        "order": order,
        "agreement": agreement,
        "agreement_label": label,
        "agreement_icon": icon,
        "items": list(order.items.all()),
        "history": list(order.status_changes.all()),
        "payment": payment,
        "can_cancel": status_service.can_cancel(order, ChangedBy.CUSTOMER),
        "returned": request.GET.get("paid") == "1",
        "tab": "profile",
        "noindex": True,
    }


@customer_required
def order_detail(request, number: str):
    order = get_object_or_404(_customer_orders(request.user), number=number)
    # Как экран заказа в приложении: незавершённая оплата сверяется при открытии.
    pending = order.payments.filter(status=PaymentStatus.PENDING).exclude(provider_payment_id=None)
    if order.payment_method == PaymentMethod.ONLINE and pending.exists():
        _sync_payment(request, order)
    order = get_object_or_404(_detail_queryset(request.user), pk=order.pk)
    # Покупатель увидел заказ — точка «есть новости» на «Профиле» гаснет (до отрисовки шапки).
    status_service.mark_seen(order)
    return render(request, "web/orders/detail.html", _order_context(request, order))


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


# --- Заказ гостя: доступ только по секретной ссылке ---


@never_cache
def guest_order(request, token: str):
    found = get_object_or_404(guest.by_token(token))
    order = get_object_or_404(_detail_queryset_of(Order.objects.filter(pk=found.pk)), pk=found.pk)
    status_service.mark_seen(order)
    # Открывший ссылку владеет заказом: при входе или регистрации он привяжется к аккаунту.
    guest_links.remember(request, token)
    context = _order_context(request, order)
    context["guest_token"] = token
    context["guest_link"] = request.build_absolute_uri()
    context["can_claim"] = request.user.is_authenticated and not request.user.is_staff
    response = render(request, "web/orders/detail.html", context)
    response["Referrer-Policy"] = "no-referrer"
    return response


@require_POST
def guest_order_cancel(request, token: str):
    order = get_object_or_404(guest.by_token(token))
    try:
        status_service.cancel(order, by=ChangedBy.CUSTOMER)
    except ValidationError as exc:
        flash_errors(request, exc)
    else:
        messages.success(request, f"Заказ {order.number} отменён.")
    return redirect("web:guest_order", token=token)


@customer_required
@require_POST
def guest_order_claim(request, token: str):
    claimed = guest.claim(request.user, [token])
    if not claimed:
        raise Http404("Заказ не найден.")
    messages.success(request, f"Заказ {claimed[0].number} теперь в вашем аккаунте.")
    return redirect("web:order", number=claimed[0].number)
