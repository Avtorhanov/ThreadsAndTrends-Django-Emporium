"""Корзина витрины. Формы работают и без JavaScript (POST → redirect); с htmx страница
обновляет только нужный фрагмент и счётчики в шапке."""

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from store.models import ProductVariant

from .. import cart as web_cart
from ..forms import AddToCartForm, CartLineForm
from .common import error_messages, flash_errors, is_htmx, safe_next


def _cart_context(request) -> dict:
    summary = web_cart.summary(request)
    return {
        "cart": summary,
        "free_delivery_from": settings.DELIVERY_FREE_FROM_KOPECKS,
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


@require_POST
def line(request, variant_id: int):
    """Количество позиции; 0 — удалить."""
    form = CartLineForm(request.POST)
    if not form.is_valid():
        return _respond(request, ["Укажите количество."])
    quantity = form.cleaned_data["quantity"]
    try:
        if quantity == 0:
            web_cart.remove(request, variant_id)
        else:
            web_cart.set_quantity(request, variant_id, quantity)
    except ValidationError as exc:
        return _respond(request, error_messages(exc))
    except Http404:
        pass  # позиция уже удалена (повторный клик, вторая вкладка) — просто показать корзину
    return _respond(request)


@require_POST
def ack_prices(request):
    try:
        web_cart.ack_prices(request)
    except ValidationError as exc:
        flash_errors(request, exc)
    return _respond(request)
