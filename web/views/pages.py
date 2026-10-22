"""Служебные страницы витрины: тема, баннер приложения, юридические страницы, robots.txt."""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST

from .. import theme
from ..context_processors import BANNER_COOKIE
from ..seo import absolute_url
from .common import safe_next

LEGAL_PAGES = {
    "offer": ("web/legal/offer.html", "Публичная оферта"),
    "privacy": ("web/legal/privacy.html", "Политика обработки персональных данных"),
    "delivery": ("web/legal/delivery.html", "Доставка, оплата и возврат"),
}


@require_POST
def set_theme(request):
    """Без JavaScript: переключатель темы — обычная форма. С JS тема меняется без перезагрузки,
    скрипт сам пишет ту же cookie."""
    value = request.POST.get("theme", "")
    response = redirect(safe_next(request, reverse("web:home")))
    return theme.apply_theme(response, value)


@require_POST
def hide_banner(request):
    response = redirect(safe_next(request, reverse("web:home")))
    response.set_cookie(BANNER_COOKIE, "hidden", max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def legal(request, page: str):
    template, title = LEGAL_PAGES[page]
    return render(
        request,
        template,
        {
            "title": title,
            "page": page,
            "delivery_courier": settings.DELIVERY_COURIER_KOPECKS,
            "delivery_free_from": settings.DELIVERY_FREE_FROM_KOPECKS,
            "pickup_address": settings.PICKUP_ADDRESS,
        },
    )


@require_GET
@cache_control(max_age=3600, public=True)
def robots_txt(request):
    lines = [
        "User-agent: *",
        # Корзина, оформление, кабинет и поиск не индексируются; API и панели — тем более.
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /orders/",
        "Disallow: /profile/",
        "Disallow: /login/",
        "Disallow: /register/",
        "Disallow: /password-reset/",
        "Disallow: /search/",
        "Disallow: /api/",
        "Disallow: /admin/",
        "Disallow: /panel/",
        "Disallow: /app/",
        "",
        f"Sitemap: {absolute_url(request, reverse('web:sitemap'))}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
