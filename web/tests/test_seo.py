import pytest
from django.urls import reverse

from content import shop as shop_settings

pytestmark = pytest.mark.django_db


def test_sitemap_contains_only_live_products_and_categories(client, shop):
    response = client.get(reverse("web:sitemap"))
    xml = response.content.decode()
    assert response.status_code == 200
    for slug in ("futbolka-belaya", "kepka", "hudi"):
        assert f"http://testserver/product/{slug}/" in xml
    for slug in ("skrytyy", "udalennyy", "v-arhive"):
        assert f"/product/{slug}/" not in xml
    assert "http://testserver/category/odezhda/" in xml
    assert "http://testserver/category/futbolki/" in xml
    assert "/category/arhiv/" not in xml
    assert "<loc>http://testserver/</loc>" in xml


def test_sitemap_uses_main_domain(client, shop, settings):
    settings.SITE_URL = "https://didi.example"
    xml = client.get(reverse("web:sitemap")).content.decode()
    assert "<loc>https://didi.example/product/kepka/</loc>" in xml


def test_robots_txt(client, db, settings):
    settings.SITE_URL = "https://didi.example"
    response = client.get("/robots.txt")
    text = response.content.decode()
    assert response["Content-Type"].startswith("text/plain")
    assert "Disallow: /checkout/" in text and "Disallow: /api/" in text
    assert "Sitemap: https://didi.example/sitemap.xml" in text


def test_canonical_uses_main_domain(client, shop, settings):
    settings.SITE_URL = "https://didi.example"
    html = client.get(reverse("web:product", args=["kepka"])).content.decode()
    assert '<link rel="canonical" href="https://didi.example/product/kepka/">' in html


def test_private_pages_are_noindex(client, customer):
    for url in (reverse("web:cart"), reverse("web:login"), reverse("web:profile")):
        assert "noindex" in client.get(url).content.decode()
    client.force_login(customer)
    assert "noindex" in client.get(reverse("web:orders")).content.decode()


@pytest.mark.parametrize("page", ["offer", "privacy", "delivery"])
def test_legal_pages(client, db, settings, page):
    settings.SELLER_NAME = "ИП Иванов И. И."
    settings.SELLER_INN = "770000000000"
    shop_settings.update(offer_enabled=True)
    html = client.get(reverse(f"web:{page}")).content.decode()
    assert ("Черновик" in html) == (page == "offer")
    if page != "delivery":
        assert "ИП Иванов И. И." in html
    assert ("770000000000" in html) == (page == "offer")
    if page != "offer":
        assert "[проверить" not in html and "[email" not in html and "[указать" not in html


def test_offer_hidden_by_default(client, db):
    assert client.get(reverse("web:offer")).url == reverse("web:privacy")
    assert reverse("web:offer") not in client.get(reverse("web:contacts")).content.decode()
    assert reverse("web:offer") not in client.get(reverse("web:register")).content.decode()


def test_offer_shown_when_enabled(client, db):
    shop_settings.update(offer_enabled=True)
    assert client.get(reverse("web:offer")).status_code == 200
    assert reverse("web:offer") in client.get(reverse("web:contacts")).content.decode()


def test_privacy_shows_operator(client, db):
    shop_settings.update(operator_name="Иван И.", operator_contact="ivan@example.com")
    html = client.get(reverse("web:privacy")).content.decode()
    assert "Иван И." in html and "ivan@example.com" in html


def test_app_banner_only_on_phones(client, db, settings):
    settings.ANDROID_APK_URL = "https://example.com/didi-shop.apk"
    android = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "https://example.com/didi-shop.apk" in android.content.decode()
    assert "data-banner" in android.content.decode()
    iphone = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)")
    iphone_html = iphone.content.decode()
    assert "На экран „Домой“" in iphone_html
    assert "/app/" not in iphone_html
    desktop = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0)")
    assert "data-banner" not in desktop.content.decode()
    client.cookies["app_banner"] = "hidden"
    hidden = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "data-banner" not in hidden.content.decode()


def test_android_banner_needs_apk_url(client, db, settings):
    settings.ANDROID_APK_URL = ""
    response = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "data-banner" not in response.content.decode()


def test_manifest_for_home_screen(client, db):
    response = client.get(reverse("web:manifest"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"
    data = response.json()
    assert data["start_url"] == "/" and data["scope"] == "/" and data["display"] == "standalone"
    assert {icon["purpose"] for icon in data["icons"]} == {"any", "maskable"}
    assert all(icon["src"].startswith("/static/web/icons/") for icon in data["icons"])
    assert "Set-Cookie" not in response
    assert client.head(reverse("web:manifest")).status_code == 200


def test_pages_link_manifest(client, db):
    html = client.get("/").content.decode()
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html
    assert 'name="apple-mobile-web-app-title"' in html
