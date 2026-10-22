"""Общий контекст шаблонов витрины. Всё, что требует запросов к БД, — ленивое: значение
считается один раз и только если шаблон к нему обратился (админка и письма не платят)."""

from functools import cache

from django.conf import settings

from store.services.storefront import category_tree

from . import cart, theme

BANNER_COOKIE = "app_banner"


def _platform(request) -> str:
    agent = request.META.get("HTTP_USER_AGENT", "")
    if "Android" in agent:
        return "android"
    if "iPhone" in agent or "iPad" in agent:
        return "ios"
    return ""


def app_banner(request) -> str:
    """Баннер «Скачать приложение» только на телефонах: Android → APK, iPhone → /app/.
    Закрытый баннер больше не показывается (cookie)."""
    if request.COOKIES.get(BANNER_COOKIE) == "hidden":
        return ""
    platform = _platform(request)
    if platform == "android" and not settings.ANDROID_APK_URL:
        return ""
    return platform


def storefront(request):
    @cache
    def cart_count():
        return cart.count(request)

    @cache
    def nav_categories():
        return category_tree()

    @cache
    def banner():
        return app_banner(request)

    return {
        "theme": theme.get_theme(request),
        "cart_count": cart_count,
        "nav_categories": nav_categories,
        "app_banner": banner,
        "android_apk_url": settings.ANDROID_APK_URL,
        "seller": {
            "name": settings.SELLER_NAME,
            "inn": settings.SELLER_INN,
            "ogrn": settings.SELLER_OGRN,
            "address": settings.SELLER_ADDRESS,
            "email": settings.SELLER_EMAIL,
            "phone": settings.SELLER_PHONE,
        },
    }
