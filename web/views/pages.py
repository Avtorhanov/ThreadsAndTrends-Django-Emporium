"""Служебные страницы витрины: тема, баннер приложения, юридические страницы, robots.txt,
манифест для установки на экран «Домой»."""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST, require_safe

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
        "",
        f"Sitemap: {absolute_url(request, reverse('web:sitemap'))}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


# Цвета — из tokens.json «Лайм-тек»: фон светлой темы и ink.
MANIFEST_BACKGROUND = "#EBF1E2"
MANIFEST_THEME = "#13261C"


@require_safe  # GET и HEAD: браузеры и проверки запрашивают манифест обоими способами
@cache_control(max_age=86400, public=True)
def manifest(request):
    """Web App Manifest витрины: «На экран Домой» на iPhone и установка из Chrome на Android
    открывают сайт без адресной строки. Адреса иконок — через static() (в prod с хэшем)."""
    icons = [
        {"src": static(f"web/icons/{name}"), "sizes": size, "type": "image/png", "purpose": purpose}
        for name, size, purpose in (
            ("icon-192.png", "192x192", "any"),
            ("icon-512.png", "512x512", "any"),
            ("icon-maskable-512.png", "512x512", "maskable"),
        )
    ]
    home = reverse("web:home")
    data = {
        "name": "DiDi-shop",
        "short_name": "DiDi-shop",
        "description": "Одежда, обувь, аксессуары и уход с доставкой.",
        "lang": "ru",
        "id": home,
        "start_url": home,
        "scope": home,
        "display": "standalone",
        "orientation": "portrait",
        "background_color": MANIFEST_BACKGROUND,
        "theme_color": MANIFEST_THEME,
        "icons": icons,
    }
    return JsonResponse(
        data,
        content_type="application/manifest+json",
        json_dumps_params={"ensure_ascii": False},
    )
