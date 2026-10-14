"""Поиск, фильтры и сортировка витрины, кэш дерева категорий."""

import pytest
from django.db import connection

from store.models import Product
from store.search import search_vector
from store.services import catalog, storefront

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/catalog/products/"
CATEGORIES = "/api/v1/catalog/categories/"


@pytest.fixture
def shop():
    clothes = make_category(name="Одежда", slug="odezhda")
    shirts = make_category(name="Футболки", slug="futbolki", parent=clothes)
    shoes = make_category(name="Обувь", slug="obuv")
    sneakers = make_category(name="Кроссовки", slug="krossovki", parent=shoes)
    return {
        "clothes": clothes,
        "shirts": shirts,
        "sneakers": sneakers,
        "white_shirt": make_product(
            name="Футболка белая",
            description="Хлопок, прямой крой",
            category=shirts,
            price_kopecks=1_490_00,
        ),
        "black_shirt": make_product(
            name="Футболка чёрная оверсайз",
            description="Плотный хлопок",
            category=shirts,
            price_kopecks=1_990_00,
        ),
        "runner": make_product(
            name="Кроссовки беговые",
            description="Лёгкая сетка для бега",
            category=sneakers,
            price_kopecks=7_990_00,
        ),
        "sold_out": make_product(
            name="Кроссовки зимние",
            description="Утеплённые",
            category=sneakers,
            price_kopecks=9_990_00,
            stock=0,
        ),
    }


def slugs(response):
    assert response.status_code == 200, response.content
    return [row["slug"] for row in response.json()["results"]]


def test_search_uses_russian_morphology_and_prefixes(api_client, shop):
    # Другая словоформа и начало слова находят товар.
    assert slugs(api_client.get(PRODUCTS, {"q": "кроссовками"})) == [shop["runner"].slug]
    assert slugs(api_client.get(PRODUCTS, {"q": "крос"})) == [shop["runner"].slug]
    # Все слова обязательны; регистр не важен.
    assert slugs(api_client.get(PRODUCTS, {"q": "ФУТБОЛКА чёрн"})) == [shop["black_shirt"].slug]


def test_search_matches_description_and_ranks_name_higher(api_client, shop):
    by_description = make_product(
        name="Майка", description="Почти футболка", category=shop["shirts"]
    )
    found = slugs(api_client.get(PRODUCTS, {"q": "футболка"}))
    # Совпадение в названии (вес A) выше совпадения в описании (вес B).
    assert set(found) == {shop["white_shirt"].slug, shop["black_shirt"].slug, by_description.slug}
    assert found[-1] == by_description.slug


def test_search_shows_only_live_products_in_stock(api_client, shop):
    hidden = make_product(name="Кроссовки скрытые", category=shop["sneakers"])
    catalog.update_product(hidden, is_active=False)
    deleted = make_product(name="Кроссовки удалённые", category=shop["sneakers"])
    catalog.soft_delete_product(deleted)

    assert slugs(api_client.get(PRODUCTS, {"q": "кроссовки"})) == [shop["runner"].slug]


@pytest.mark.parametrize("text", ["!!!", "   ", "& | : * ( )", "'); DROP TABLE x; --"])
def test_search_ignores_tsquery_syntax(api_client, shop, text):
    response = api_client.get(PRODUCTS, {"q": text})
    assert response.status_code == 200
    # Запрос без слов — обычная лента.
    if not any(ch.isalnum() for ch in text):
        assert response.json()["count"] == 4


def test_filters_by_category_price_and_stock(api_client, shop):
    assert slugs(api_client.get(PRODUCTS, {"category": "obuv"})) == [
        shop["sold_out"].slug,
        shop["runner"].slug,
    ]
    assert slugs(api_client.get(PRODUCTS, {"category": "obuv", "in_stock": "true"})) == [
        shop["runner"].slug
    ]
    assert slugs(
        api_client.get(
            PRODUCTS, {"price_min": 1_500_00, "price_max": 8_000_00, "sort": "price_asc"}
        )
    ) == [shop["black_shirt"].slug, shop["runner"].slug]


def test_sorting(api_client, shop):
    by_price = slugs(api_client.get(PRODUCTS, {"sort": "price_desc"}))
    assert by_price == [
        shop["sold_out"].slug,
        shop["runner"].slug,
        shop["black_shirt"].slug,
        shop["white_shirt"].slug,
    ]
    # По умолчанию — новые первыми.
    assert slugs(api_client.get(PRODUCTS))[0] == shop["sold_out"].slug


@pytest.mark.parametrize(
    "params, field",
    [
        ({"price_min": -1}, "price_min"),
        ({"price_min": "abc"}, "price_min"),
        ({"price_min": 500, "price_max": 100}, "price_max"),
        ({"sort": "random"}, "sort"),
        ({"q": "x" * 101}, "q"),
    ],
)
def test_invalid_params_are_400(api_client, shop, params, field):
    response = api_client.get(PRODUCTS, params)
    assert response.status_code == 400
    assert field in response.json()


def test_search_query_count_is_constant(api_client, shop, django_assert_max_num_queries):
    for n in range(5):
        make_product(name=f"Кроссовки {n}", category=shop["sneakers"], sizes=("40", "41"))
    # count + товары + изображения (prefetch), без N+1.
    with django_assert_max_num_queries(3):
        response = api_client.get(PRODUCTS, {"q": "кроссовки", "sort": "price_asc"})
    assert response.json()["count"] == 6


def test_search_uses_gin_index(shop):
    """Выражение запроса совпадает с индексом product_search_idx (иначе — полный перебор)."""
    query = Product.objects.annotate(search=search_vector()).filter(
        search=storefront.build_search_query("кроссовки")
    )
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute("SET LOCAL enable_indexscan = off")
        plan = query.explain()
    assert "product_search_idx" in plan


def test_search_vector_matches_index_expression():
    index = next(i for i in Product._meta.indexes if i.name == "product_search_idx")
    assert str(index.expressions[0]) == str(search_vector())


# --- Кэш дерева категорий ---


def test_category_tree_is_cached_and_invalidated(api_client, shop, django_assert_num_queries):
    first = api_client.get(CATEGORIES).json()
    with django_assert_num_queries(0):
        assert api_client.get(CATEGORIES).json() == first

    catalog.update_category(shop["shirts"], name="Майки и футболки")
    tree = api_client.get(CATEGORIES).json()
    assert tree[0]["children"][0]["name"] == "Майки и футболки"

    catalog.update_category(shop["sneakers"], is_active=False)
    tree = api_client.get(CATEGORIES).json()
    assert [root["children"] for root in tree if root["slug"] == "obuv"] == [[]]
