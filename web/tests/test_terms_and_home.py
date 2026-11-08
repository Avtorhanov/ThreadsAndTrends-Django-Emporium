"""Витрина: условия у товара и страница доставки — от настроек; полоса категорий на главной."""

import pytest
from django.core.cache import cache
from django.urls import reverse

from content import shop as shop_settings
from content.models import ShopSettings
from store.tests.factories import make_category, make_product

pytestmark = pytest.mark.django_db


def configure(settings, *, online=False, agreement=True, cash=False, courier=None, free_from=None):
    settings.ORDERS_ONLINE_PAYMENT_ENABLED = online
    ShopSettings.objects.update_or_create(
        pk=1,
        defaults={
            "online_payment_enabled": online,
            "agreement_enabled": agreement,
            "cash_on_delivery_enabled": cash,
            "delivery_courier_kopecks": courier,
            "delivery_free_from_kopecks": free_from,
        },
    )
    cache.delete(shop_settings.CACHE_KEY)


def delivery_page(client) -> str:
    return client.get(reverse("web:delivery")).content.decode()


def test_delivery_page_lists_only_agreement(client, settings):
    configure(settings)
    html = delivery_page(client)
    assert "По согласованию с продавцом" in html
    assert "ЮKassa" not in html
    assert "При получении —" not in html
    assert "чек приходит" not in html
    assert "оплачен онлайн" not in html


def test_delivery_page_lists_online_and_cash(client, settings):
    configure(settings, online=True, agreement=False, cash=True)
    html = delivery_page(client)
    assert "ЮKassa" in html
    assert "При получении —" in html
    assert "чек приходит" in html
    assert "По согласованию с продавцом" not in html


def test_default_meta_does_not_promise_payment(client, db):
    html = client.get(reverse("web:products")).content.decode()
    head = html[: html.index("</head>")]
    assert "при получении" not in head.lower()
    assert "оплата онлайн" not in head.lower()


def test_terms_use_shop_settings_and_active_methods(client, settings):
    configure(settings, courier=30_000, free_from=700_000)
    product = make_product("Футболка", category=make_category("Одежда", slug="wear"))
    html = client.get(reverse("web:product", args=[product.slug])).content.decode()
    assert "300&nbsp;₽" in html
    assert "7 000&nbsp;₽" in html.replace(" ", " ")
    assert "по согласованию с продавцом" in html
    assert "онлайн картой" not in html
    assert reverse("web:delivery") in html


def test_terms_on_request_have_no_payment(client, settings):
    configure(settings)
    category = make_category("LUXE", slug="luxe")
    product = make_product("Лоферы", category=category, slug="lofery", price_kopecks=None)
    html = client.get(reverse("web:product", args=[product.slug])).content.decode()
    assert "Доставка курьером" in html
    assert "по согласованию с продавцом" not in html


def test_buttons_above_description_and_size_message(client, settings):
    configure(settings)
    product = make_product(
        "Кроссовки", category=make_category("Обувь", slug="shoes"), description="Описание товара"
    )
    html = client.get(reverse("web:product", args=[product.slug])).content.decode()
    assert html.index("data-cta") < html.index("pd__desc")


def test_stock_limit_text_default_and_custom(client, settings):
    configure(settings)
    product = make_product("Куртка", category=make_category("Одежда", slug="wear"))
    url = reverse("web:product", args=[product.slug])
    html = client.get(url).content.decode()
    assert f'data-limit-text="{shop_settings.DEFAULT_STOCK_LIMIT_TEXT}"' in html
    ShopSettings.objects.filter(pk=1).update(stock_limit_text="Это последний")
    cache.delete(shop_settings.CACHE_KEY)
    assert 'data-limit-text="Это последний"' in client.get(url).content.decode()
