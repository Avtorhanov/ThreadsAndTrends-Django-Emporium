import json
import re

import pytest
from django.urls import reverse

from content import services
from orders.models import OrderStatus
from orders.tests.factories import make_order

from .conftest import image_file

pytestmark = pytest.mark.django_db


@pytest.fixture
def articles(db, django_capture_on_commit_callbacks):
    published = services.create_article(
        title="Как выбрать размер",
        excerpt="Таблица размеров",
        body="Измерьте обхват груди.\n\nСверьтесь с таблицей <b>размеров</b>.",
        is_published=True,
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.add_article_image(published, image_file())
        services.add_article_image(published, image_file())
    draft = services.create_article(title="Черновик статьи")
    return {"published": published, "draft": draft}


def test_contacts_page_lists_channels_and_articles(client, articles, settings):
    settings.CONTACT_WHATSAPP = "+7 900 123-45-67"
    settings.CONTACT_TELEGRAM = "@didishop"
    settings.CONTACT_VK = ""
    html = client.get(reverse("web:contacts")).content.decode()
    assert 'href="https://wa.me/79001234567"' in html and "+7 900 123-45-67" in html
    assert 'href="https://t.me/didishop"' in html and 'rel="noopener noreferrer"' in html
    assert "vk.com" not in html
    assert "Instagram" not in html
    assert "Как выбрать размер" in html and "Таблица размеров" in html
    assert "Черновик статьи" not in html
    # Вкладка «Контакты» активна в нижней панели; «Поиска» во вкладках больше нет.
    assert re.search(r'class="tab is-on" href="/contacts/"', html)
    tabbar = html.split('class="tabbar"')[1]
    assert "/search/" not in tabbar


def test_contacts_page_without_channels(client, db):
    html = client.get(reverse("web:contacts")).content.decode()
    assert "Контакты скоро появятся" in html


def test_article_page(client, articles):
    response = client.get(reverse("web:article", args=["kak-vybrat-razmer"]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "<title>Как выбрать размер — DiDi-shop</title>" in html
    assert '<meta property="og:type" content="article">' in html
    assert "<p>Измерьте обхват груди.</p>" in html
    # Текст статьи — без HTML: теги экранируются.
    assert "&lt;b&gt;размеров&lt;/b&gt;" in html and "<b>размеров</b>" not in html
    assert html.count('class="post__photo') == 1  # вторая фотография — в галерее
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    assert json.loads(raw)["@type"] == "Article"


def test_draft_and_deleted_articles_are_404(client, articles):
    assert client.get(reverse("web:article", args=[articles["draft"].slug])).status_code == 404
    services.delete_article(articles["published"])
    assert client.get(reverse("web:article", args=["kak-vybrat-razmer"])).status_code == 404


def test_sitemap_contains_published_articles_only(client, articles):
    xml = client.get(reverse("web:sitemap")).content.decode()
    assert "/articles/kak-vybrat-razmer/" in xml
    assert articles["draft"].slug not in xml
    assert "http://testserver/contacts/" in xml


def test_profile_shows_current_order_and_help(customer_client, customer):
    make_order(customer, status=OrderStatus.DELIVERED)
    current = make_order(customer, status=OrderStatus.CONFIRMED)
    html = customer_client.get(reverse("web:profile")).content.decode()
    assert "Текущий заказ" in html and current.number in html
    assert reverse("web:delivery") in html.split('aria-label="Помощь"')[1]
    assert reverse("web:contacts") in html.split('aria-label="Помощь"')[1]


def test_profile_without_current_order(customer_client, customer):
    make_order(customer, status=OrderStatus.CANCELLED)
    assert "Текущий заказ" not in customer_client.get(reverse("web:profile")).content.decode()


def test_guest_profile_has_help(client, db):
    assert 'aria-label="Помощь"' in client.get(reverse("web:profile")).content.decode()
