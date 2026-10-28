"""Корзина витрины. Формы работают и без JavaScript (POST → redirect); с htmx страница
обновляет только нужный фрагмент и счётчики в шапке."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.http import require_POST

from content import shop as shop_settings
from store.models import ProductVariant

from .. import cart as web_cart
from ..forms import AddToCartForm, CartLineForm
from .common import error_messages, flash_errors, is_htmx, safe_next


def _cart_context(request) -> dict:
    summary = web_cart.summary(request)
    return {
        "cart": summary,
        "free_delivery_from": shop_settings.current().delivery_free_from_kopecks,
        "tab": "cart",
        "noindex": True,
    }


def cart_page(request):
    return render(request, "web/cart/cart.html", _cart_context(request))


@require_POST
def add(request):
    form = AddToCartForm(request.POST)
    back = safe_next(request, reverse("web:cart"))
    errors: list[str] = []
    variant = None
    if not form.is_valid():
        errors = ["Выберите размер."]
    else:
        variant = (
            ProductVariant.objects.select_related("product")
            .filter(pk=form.cleaned_data["variant"])
            .first()
        )
        try:
            web_cart.add(request, form.cleaned_data["variant"], form.cleaned_data["quantity"] or 1)
        except ValidationError as exc:
            errors = error_messages(exc)

    if is_htmx(request):
        # Фрагмент кнопки: «Добавлено в корзину» с заливкой или ошибка под кнопкой;
        # счётчики корзины в шапке и нижней панели обновляются тем же ответом (hx-swap-oob).
        return render(
            request,
            "web/cart/_added.html",
            {
                "errors": errors,
                "product": variant.product if variant else None,
                "cart_count": web_cart.count(request),
            },
            status=200,
        )
    for text in errors:
        messages.error(request, text)
    if not errors:
        messages.success(request, "Добавлено в корзину")
    return redirect(back)


@require_POST
def buy_now(request):
    """«Купить сейчас» из карточки товара: к оформлению только выбранного размера, корзина
    не меняется. Без JS — обычная отправка формы (formaction), с htmx — HX-Redirect."""
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        if is_htmx(request):
            context = {"errors": ["Выберите размер."], "cart_count": web_cart.count(request)}
            return render(request, "web/cart/_added.html", context)
        messages.error(request, "Выберите размер.")
        return redirect(safe_next(request, reverse("web:home")))
    data = form.cleaned_data
    query = urlencode({"variant": data["variant"], "qty": data["quantity"] or 1})
    url = f"{reverse('web:checkout')}?{query}"
    if is_htmx(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


def _respond(request, errors: list[str] | None = None):
    if is_htmx(request):
        context = _cart_context(request)
        context["errors"] = errors or []
        context["cart_count"] = web_cart.count(request)
        context["oob_badges"] = True
        return render(request, "web/cart/_cart.html", context)
    for text in errors or []:
        messages.error(request, text)
    return redirect("web:cart")


def _respond_line(request, variant_id: int, errors: list[str] | None = None):
    """Ответ htmx на «+/−»: только эта позиция, итог и счётчики — остальная корзина
    (фото, названия, другие позиции) не перерисовывается. Корзина опустела — вся корзина."""
    context = _cart_context(request)
    cart = context["cart"]
    if not cart.lines:
        context["cart_count"] = 0
        context["oob_badges"] = True
        response = render(request, "web/cart/_cart.html", context)
        response["HX-Retarget"] = "#cart"
        response["HX-Reswap"] = "outerHTML"
        return response
    context.update(
        line=next((line for line in cart.lines if line.variant_id == variant_id), None),
        variant_id=variant_id,
        line_errors=errors or [],
        cart_count=web_cart.count(request),
    )
    return render(request, "web/cart/_line_update.html", context)


@require_POST
def line(request, variant_id: int):
    """Количество позиции; 0 — удалить."""
    form = CartLineForm(request.POST)
    errors: list[str] = []
    if not form.is_valid():
        errors = ["Укажите количество."]
    else:
        quantity = form.cleaned_data["quantity"]
        try:
            if quantity == 0:
                web_cart.remove(request, variant_id)
            else:
                web_cart.set_quantity(request, variant_id, quantity)
        except ValidationError as exc:
            errors = error_messages(exc)
        except Http404:
            pass  # позиция уже удалена (повторный клик, вторая вкладка) — просто показать корзину
    if is_htmx(request):
        return _respond_line(request, variant_id, errors)
    return _respond(request, errors)


@require_POST
def ack_prices(request):
    try:
        web_cart.ack_prices(request)
    except ValidationError as exc:
        flash_errors(request, exc)
    return _respond(request)
