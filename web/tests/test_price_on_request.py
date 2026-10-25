"""Витрина: товар с ценой по запросу — «По запросу» в ленте, «Узнать» вместо корзины."""

import json
import re

import pytest
from django.urls import reverse

from store.tests.factories import make_category, make_product

pytestmark = pytest.mark.django_db


@pytest.fixture
def luxe(db):
    category = make_category("LUXE", slug="luxe")
    return make_product("Лоферы Gucci", category=category, slug="lofery", price_kopecks=None)


def test_card_shows_on_request(client, luxe):
    html = client.get(reverse("web:category", args=["luxe"])).content.decode()
    assert "По запросу" in html
    assert "None" not in html


def test_product_page_offers_messengers_instead_of_cart(client, settings, luxe):
    settings.CONTACT_TELEGRAM = "@didishop"
    settings.CONTACT_WHATSAPP = "+7 900 123-45-67"
    html = client.get(reverse("web:product", args=[luxe.slug])).content.decode()
    assert "Цена по запросу" in html
    assert "data-ask" in html and ">Узнать<" in html
    assert 'href="https://t.me/didishop"' in html
    # В WhatsApp вопрос подставляется в чат: название и ссылка на товар.
    wa = re.search(r'href="(https://wa\.me/79001234567\?text=[^"]+)"', html)
    assert wa and "%D0%9B%D0%BE%D1%84%D0%B5%D1%80%D1%8B" in wa.group(1)
    assert reverse("web:cart_add") not in html
    assert "None" not in html


def test_product_page_without_messengers_links_contacts(client, settings, luxe):
    settings.CONTACT_TELEGRAM = ""
    settings.CONTACT_WHATSAPP = ""
    html = client.get(reverse("web:product", args=[luxe.slug])).content.decode()
    assert f'href="{reverse("web:contacts")}"' in html


def test_schema_has_no_offer_without_price(client, luxe):
    html = client.get(reverse("web:product", args=[luxe.slug])).content.decode()
    raw = re.search(r'<script type="application/ld\+json">(.+?)</script>', html, re.S).group(1)
    data = json.loads(raw)
    assert data["@type"] == "Product" and "offers" not in data
    assert "product:price:amount" not in html


def test_cart_add_is_refused(client, luxe):
    response = client.post(
        reverse("web:cart_add"),
        {"variant": luxe.variants.get().pk},
        HTTP_HX_REQUEST="true",
    )
    assert "по запросу" in response.content.decode()
    assert client.get(reverse("web:cart")).context["cart"].lines == []


def test_priced_product_still_has_cart(client):
    product = make_product("Футболка", slug="futbolka", price_kopecks=1_000_00)
    html = client.get(reverse("web:product", args=[product.slug])).content.decode()
    assert reverse("web:cart_add") in html and "data-ask" not in html
