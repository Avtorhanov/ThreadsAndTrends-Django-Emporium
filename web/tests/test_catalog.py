import json
import re

import pytest
from django.urls import reverse

from store.models import Product
from store.services.catalog import add_product_image
from store.tests.factories import make_product

from .conftest import image_file

pytestmark = pytest.mark.django_db


def json_ld(html: str) -> dict:
    raw = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1)
    return json.loads(raw)


def test_home_lists_live_products(client, shop):
    response = client.get("/")
    html = response.content.decode()
    assert response.status_code == 200
    assert "Футболка белая" in html and "Кепка" in html and "Худи" in html
    for name in ("Скрытый", "Удалённый", "В архиве"):
        assert name not in html
    # Тема без cookie — системная: data-theme на <html> не ставится.
    assert '<html lang="ru">' in html
    assert '<link rel="canonical" href="http://testserver/">' in html


def test_theme_cookie_is_rendered_on_server(client, shop):
    client.cookies["theme"] = "dark"
    assert '<html lang="ru" data-theme="dark">' in client.get("/").content.decode()
    client.cookies["theme"] = "neon"
    assert '<html lang="ru">' in client.get("/").content.decode()


def test_set_theme_without_javascript(client, db):
    response = client.post(reverse("web:theme"), {"theme": "dark", "next": "/cart/"})
    assert response.status_code == 302 and response["Location"] == "/cart/"
    assert response.cookies["theme"].value == "dark"
    response = client.post(reverse("web:theme"), {"theme": "system"})
    assert response.cookies["theme"].value == ""  # удалена — снова системная


def test_category_page_includes_subcategories_and_canonical(client, shop):
    response = client.get(reverse("web:category", args=["odezhda"]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Футболка белая" in html and "Кепка" in html
    assert '<link rel="canonical" href="http://testserver/category/odezhda/">' in html
    assert 'name="robots"' not in html
    assert reverse("web:category", args=["futbolki"]) in html  # подкатегория


def test_hidden_category_is_404(client, shop):
    assert client.get(reverse("web:category", args=["arhiv"])).status_code == 404


def test_filters_and_sorting_are_noindex(client, shop):
    response = client.get(
        reverse("web:products"), {"sort": "price_asc", "price_min": "1000", "in_stock": "1"}
    )
    html = response.content.decode()
    assert '<meta name="robots" content="noindex, follow">' in html
    assert "Кепка" not in html.split('class="grid"')[1]  # 990 ₽ < 1 000 ₽
    assert "Худи" not in html.split('class="grid"')[1]  # нет в наличии


def test_price_in_rubles_is_parsed_without_float(client, shop):
    html = client.get(reverse("web:products"), {"price_max": "990,00"}).content.decode()
    grid = html.split('class="grid"')[1]
    assert "Кепка" in grid and "Футболка белая" not in grid


def test_search_page(client, shop):
    response = client.get(reverse("web:search"), {"q": "футб"})
    html = response.content.decode()
    assert response.status_code == 200
    assert "noindex" in html
    assert "Футболка белая" in html.split('class="grid"')[1]


def test_garbage_params_do_not_break_listing(client, shop):
    response = client.get(
        reverse("web:products"),
        {"sort": "nope", "price_min": "abc", "q": "x" * 500, "in_stock": "maybe"},
    )
    assert response.status_code == 200


def test_pagination(client, shop, settings):
    settings.WEB_PAGE_SIZE = 2
    first = client.get(reverse("web:products")).content.decode()
    assert 'href="/products/?page=2"' in first and 'rel="next"' in first
    second = client.get(reverse("web:products"), {"page": 2})
    assert second.status_code == 200
    assert '<link rel="canonical" href="http://testserver/products/?page=2">' in (
        second.content.decode()
    )
    assert client.get(reverse("web:products"), {"page": 99}).status_code == 404
    assert client.get(reverse("web:products"), {"page": "x"}).status_code == 404


def test_listing_query_count_does_not_grow_with_products(
    client, shop, django_assert_max_num_queries
):
    url = reverse("web:category", args=["odezhda"])
    client.get(url)  # прогрев: дерево категорий в кэше
    with django_assert_max_num_queries(12) as small:
        client.get(url + "?sort=price_desc")
    for n in range(15):
        make_product(f"Товар {n}", category=shop["tees"])
    with django_assert_max_num_queries(len(small.captured_queries)):
        client.get(url + "?sort=price_asc")


def test_grid_is_cached_and_reset_on_catalog_change(client, shop, django_assert_num_queries):
    client.get("/")
    html = client.get("/").content.decode()
    assert "Кепка" in html
    shop["cap"].name = "Панама"
    shop["cap"].save()
    assert "Панама" in client.get("/").content.decode()


def test_product_page(client, shop):
    response = client.get(reverse("web:product", args=["futbolka-belaya"]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "<title>Футболка белая — купить за 1\u00a0990 ₽ в DiDi-shop</title>" in html
    assert '<link rel="canonical" href="http://testserver/product/futbolka-belaya/">' in html
    assert '<meta property="og:type" content="product">' in html
    assert "−20%" in html
    data = json_ld(html)
    assert data["@type"] == "Product" and data["name"] == "Футболка белая"
    assert data["offers"]["price"] == "1990.00"
    assert data["offers"]["priceCurrency"] == "RUB"
    assert data["offers"]["availability"] == "https://schema.org/InStock"
    assert 'name="variant"' in html and ">S<" in html and ">M<" in html


def test_sold_out_product_is_marked_out_of_stock(client, shop):
    html = client.get(reverse("web:product", args=["hudi"])).content.decode()
    assert json_ld(html)["offers"]["availability"] == "https://schema.org/OutOfStock"
    assert "Нет в наличии" in html


def test_json_ld_cannot_close_script_tag(client, shop):
    shop["shirt"].description = "</script><script>alert(1)</script>"
    shop["shirt"].save()
    html = client.get(reverse("web:product", args=["futbolka-belaya"])).content.decode()
    assert "<script>alert(1)" not in html
    assert json_ld(html)["description"].startswith("</script>")


@pytest.mark.parametrize("key", ["hidden", "deleted", "archived"])
def test_hidden_and_deleted_products_are_404(client, shop, key):
    product = Product.all_objects.get(pk=shop[key].pk)
    assert client.get(reverse("web:product", args=[product.slug])).status_code == 404


def test_product_images_have_srcset_after_thumbnails(
    client, shop, django_capture_on_commit_callbacks
):
    # Задача превью ставится после commit и в тестах выполняется сразу (ImmediateBackend).
    with django_capture_on_commit_callbacks(execute=True):
        image = add_product_image(shop["shirt"], image_file())
    image.refresh_from_db()
    assert image.thumbs_ready and (image.width, image.height) == (1200, 1500)
    html = client.get(reverse("web:product", args=["futbolka-belaya"])).content.decode()
    assert ".w480.webp 480w" in html and ".w960.webp 960w" in html and "1200w" in html
    assert 'width="1200" height="1500"' in html
    assert 'fetchpriority="high"' in html


def test_404_page_uses_storefront_design(client, db):
    response = client.get("/no-such-page/")
    assert response.status_code == 404
    assert "Такой страницы нет" in response.content.decode()


def test_security_headers(client, db):
    response = client.get("/")
    assert "script-src 'self'" in response["Content-Security-Policy"]
    assert response["Referrer-Policy"] == "strict-origin-when-cross-origin"
