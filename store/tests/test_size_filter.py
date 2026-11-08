"""Фильтр по размеру: значения по RU, только варианты с остатком, число запросов."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from store.models import ProductVariant
from store.services import storefront
from store.sizes import size_group, sort_sizes

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/catalog/products/"
SIZES = "/api/v1/catalog/products/sizes/"


def names(response) -> set[str]:
    assert response.status_code == 200, response.content
    return {row["name"] for row in response.json()["results"]}


@pytest.fixture
def shop():
    shoes = make_category(name="Обувь", slug="obuv")
    tees = make_category(name="Футболки", slug="futbolki")
    make_product("Кеды женские", shoes, sizes=("38 · 8 US", "39 · 8,5 US"))
    make_product("Кеды мужские", shoes, sizes=("38 · 6,5 US",))
    make_product("Кроссовки поставщика", shoes, sizes=("38", "8 US"))
    make_product("Футболка", tees, sizes=("M", "S", "XL"))
    make_product("Панама", tees, sizes=("",))
    make_product("Распродано", tees, stock=0, sizes=("XXL",))
    return {"shoes": shoes, "tees": tees}


def test_size_group_and_order():
    assert size_group("38 · 8 US") == "38"
    assert size_group("8 US") == "8 US"
    assert sort_sizes(["10–12 лет", "9,5 US", "8 US", "122", "38", "XL", "S"]) == [
        "S",
        "XL",
        "38",
        "122",
        "8 US",
        "9,5 US",
        "10–12 лет",
    ]


def test_clean_sizes():
    assert storefront.clean_sizes(["", " ", "38 · 8 US", "38", "S"]) == ("S", "38")
    assert len(storefront.clean_sizes(str(n) for n in range(100))) == storefront.MAX_FILTER_SIZES


def test_ru_size_finds_every_notation(api_client, shop):
    assert names(api_client.get(PRODUCTS, {"size": "38"})) == {
        "Кеды женские",
        "Кеды мужские",
        "Кроссовки поставщика",
    }


def test_several_sizes_mean_any(api_client, shop):
    found = names(api_client.get(PRODUCTS, {"size": ["39", "M"]}))
    assert found == {"Кеды женские", "Футболка"}


def test_us_size_does_not_match_ru(api_client, shop):
    assert names(api_client.get(PRODUCTS, {"size": "8 US"})) == {"Кроссовки поставщика"}


def test_only_variants_in_stock(api_client, shop):
    assert names(api_client.get(PRODUCTS, {"size": "XXL"})) == set()
    ProductVariant.objects.filter(size="M").update(stock=0)
    assert names(api_client.get(PRODUCTS, {"size": "M"})) == set()
    assert "M" not in api_client.get(SIZES).json()["sizes"]


def test_deleted_variant_is_ignored(api_client, shop):
    ProductVariant.objects.filter(size="XL").update(deleted_at=timezone.now())
    assert names(api_client.get(PRODUCTS, {"size": "XL"})) == set()
    assert "XL" not in api_client.get(SIZES).json()["sizes"]


def test_sizes_follow_current_selection(api_client, shop):
    assert api_client.get(SIZES, {"category": "futbolki"}).json()["sizes"] == ["S", "M", "XL"]
    assert api_client.get(SIZES, {"q": "кеды"}).json()["sizes"] == ["38", "39"]
    assert api_client.get(SIZES).json()["sizes"] == ["S", "M", "XL", "38", "39", "8 US"]


def test_chosen_size_does_not_narrow_sizes(api_client, shop):
    response = api_client.get(SIZES, {"category": "futbolki", "size": "M"})
    assert response.json()["sizes"] == ["S", "M", "XL"]


def test_sizes_are_one_query_at_any_catalog_size(api_client, shop):
    with CaptureQueriesContext(connection) as small:
        api_client.get(SIZES)
    for n in range(10):
        make_product(f"Товар {n}", shop["tees"], sizes=(str(40 + n), "S"))
    with CaptureQueriesContext(connection) as large:
        api_client.get(SIZES)
    assert len(large) == len(small) == 1


def test_list_query_count_does_not_grow_with_size_filter(api_client, shop):
    with CaptureQueriesContext(connection) as plain:
        api_client.get(PRODUCTS)
    with CaptureQueriesContext(connection) as filtered:
        api_client.get(PRODUCTS, {"size": ["38", "M"]})
    assert len(filtered) <= len(plain)
