import pytest
from django.urls import reverse

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
    html = client.get(reverse(f"web:{page}")).content.decode()
    assert "Черновик" in html
    if page != "delivery":
        assert "ИП Иванов И. И." in html and "770000000000" in html


def test_app_banner_only_on_phones(client, db, settings):
    settings.ANDROID_APK_URL = "https://example.com/didi-shop.apk"
    android = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "https://example.com/didi-shop.apk" in android.content.decode()
    assert "data-banner" in android.content.decode()
    iphone = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)")
    assert 'href="/app/">Открыть' in iphone.content.decode()
    desktop = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0)")
    assert "data-banner" not in desktop.content.decode()
    client.cookies["app_banner"] = "hidden"
    hidden = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "data-banner" not in hidden.content.decode()


def test_android_banner_needs_apk_url(client, db, settings):
    settings.ANDROID_APK_URL = ""
    response = client.get("/", HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) Mobile")
    assert "data-banner" not in response.content.decode()
