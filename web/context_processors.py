"""Общий контекст шаблонов витрины. Всё, что требует запросов к БД, — ленивое: значение
считается один раз и только если шаблон к нему обратился (админка и письма не платят)."""

from functools import cache

from django.conf import settings

from content import look
from content import shop as shop_settings
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
    """Баннер только на телефонах: Android → APK, iPhone → «На экран Домой» для сайта.
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

    @cache
    def cart_slugs():
        return cart.product_slugs(request)

    @cache
    def seller():
        # Реквизиты из панели («Настройки»), пустое поле — из .env.
        return shop_settings.current().seller

    @cache
    def seller_line():
        # Заполненные реквизиты одной строкой подвала; пустые не показываются.
        return seller().parts()

    return {
        "theme": theme.get_theme(request),
        "look": theme.get_look(request),
        # Вид нижнего меню (панель → «Тема»); «Сплошное» — без атрибута на <html>.
        "nav_style": look.shop_theme().nav_style,
        "cart_count": cart_count,
        "nav_categories": nav_categories,
        "app_banner": banner,
        "cart_slugs": cart_slugs,
        "android_apk_url": settings.ANDROID_APK_URL,
        "seller": seller,
        "seller_line": seller_line,
    }
