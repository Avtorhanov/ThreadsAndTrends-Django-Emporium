import pytest

from store.services import catalog

from .conftest import image_file
from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

CATEGORIES = "/api/v1/catalog/categories/"
PRODUCTS = "/api/v1/catalog/products/"


@pytest.fixture
def tree():
    clothes = make_category(name="Одежда", slug="odezhda", position=0)
    shirts = make_category(name="Футболки", slug="futbolki", parent=clothes)
    hidden_child = make_category(name="Архив", slug="arkhiv", parent=clothes, is_active=False)
    shoes = make_category(name="Обувь", slug="obuv", position=1)
    hidden_root = make_category(name="Скрытая", slug="skrytaya", is_active=False)
    hidden_root_child = make_category(name="Внутри", slug="vnutri", parent=hidden_root)
    return {
        "clothes": clothes,
        "shirts": shirts,
        "hidden_child": hidden_child,
        "shoes": shoes,
        "hidden_root_child": hidden_root_child,
    }


def test_category_tree_contains_only_active(api_client, tree):
    response = api_client.get(CATEGORIES)
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": tree["clothes"].pk,
            "slug": "odezhda",
            "name": "Одежда",
            "children": [{"id": tree["shirts"].pk, "slug": "futbolki", "name": "Футболки"}],
        },
        {"id": tree["shoes"].pk, "slug": "obuv", "name": "Обувь", "children": []},
    ]


def test_invalid_bearer_token_does_not_break_public_catalog(api_client, tree):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired.or.garbage")
    assert api_client.get(PRODUCTS).status_code == 200


def test_product_list_shows_only_live_products(api_client, tree):
    visible = make_product(category=tree["shirts"], price_kopecks=1_990_00)
    make_product(category=tree["shirts"], is_active=False)
    make_product(category=tree["shirts"], deleted_at="2026-01-01T00:00:00Z")
    make_product(category=tree["hidden_child"])
    make_product(category=tree["hidden_root_child"])

    response = api_client.get(PRODUCTS)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    row = data["results"][0]
    assert row == {
        "id": visible.pk,
        "slug": visible.slug,
        "name": visible.name,
        "price_kopecks": 199000,
        "compare_at_kopecks": None,
        "in_stock": True,
        "cover_url": None,
        "category": {"id": tree["shirts"].pk, "slug": "futbolki", "name": "Футболки"},
    }


def test_product_list_category_filter_includes_children(api_client, tree):
    shirt = make_product(category=tree["shirts"])
    make_product(category=tree["shoes"])

    rows = api_client.get(PRODUCTS, {"category": "odezhda"}).json()["results"]
    assert [row["id"] for row in rows] == [shirt.pk]
    assert api_client.get(PRODUCTS, {"category": "nope"}).status_code == 404
    assert api_client.get(PRODUCTS, {"category": "arkhiv"}).status_code == 404


def test_product_list_query_count_is_constant(api_client, tree, django_assert_max_num_queries):
    for _ in range(5):
        product = make_product(category=tree["shirts"], sizes=("S", "M"))
        catalog.add_product_image(product, image_file())
    # count + товары + изображения (prefetch), без N+1.
    with django_assert_max_num_queries(3):
        response = api_client.get(PRODUCTS)
    assert all(row["cover_url"] for row in response.json()["results"])


def test_product_detail(api_client, tree):
    product = make_product(
        category=tree["shirts"], sizes=("S", "M"), stock=0, compare_at_kopecks=200_00
    )
    small, medium = product.variants.all()
    catalog.update_variant(medium, stock=2)
    catalog.delete_variant(small)
    image = catalog.add_product_image(product, image_file())

    response = api_client.get(f"{PRODUCTS}{product.slug}/")
    assert response.status_code == 200
    data = response.json()
    assert data["in_stock"] is True
    assert data["compare_at_kopecks"] == 200_00
    assert data["variants"] == [{"id": medium.pk, "size": "M", "in_stock": True}]
    assert data["images"] == [{"id": image.pk, "url": data["cover_url"]}]
    assert data["cover_url"].startswith("http://testserver/media/products/")
    assert "stock" not in data["variants"][0]  # точные остатки клиенту не раскрываются


@pytest.mark.parametrize("state", ["inactive", "deleted"])
def test_hidden_product_detail_is_404(api_client, tree, state):
    product = make_product(category=tree["shirts"])
    if state == "inactive":
        catalog.update_product(product, is_active=False)
    else:
        catalog.soft_delete_product(product)
    assert api_client.get(f"{PRODUCTS}{product.slug}/").status_code == 404
