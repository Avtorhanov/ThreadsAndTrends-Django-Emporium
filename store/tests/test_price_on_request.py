"""Цена по запросу: товар без цены виден в каталоге, но не продаётся через корзину."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from store.models import CartItem, Product
from store.services import cart as cart_service
from store.services import catalog
from store.services.cart import LineInput, LineStatus
from store.services.storefront import ProductFilters, Sort, filter_products

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db


@pytest.fixture
def luxe():
    return make_product("Лоферы", price_kopecks=None, slug="lofery")


def test_service_creates_product_without_price():
    product = catalog.create_product(name="Сумка", category=make_category(), price_kopecks=None)
    assert product.price_kopecks is None
    assert product.price_on_request


def test_old_price_requires_price():
    with pytest.raises(ValidationError) as exc:
        catalog.create_product(
            name="Сумка", category=make_category(), price_kopecks=None, compare_at_kopecks=500_00
        )
    assert "compare_at_kopecks" in exc.value.message_dict


def test_update_removes_price(luxe):
    product = make_product(price_kopecks=1_000_00)
    catalog.update_product(product, price_kopecks=None)
    product.refresh_from_db()
    assert product.price_on_request


def test_database_rejects_old_price_without_price(luxe):
    luxe.compare_at_kopecks = 100_00
    with pytest.raises(IntegrityError), transaction.atomic():
        luxe.save(update_fields=["compare_at_kopecks"])


def test_cart_add_is_refused(customer, luxe):
    with pytest.raises(ValidationError) as exc:
        cart_service.add(customer, luxe.variants.get().pk)
    assert exc.value.code == "price_on_request"
    assert not CartItem.objects.exists()


def test_guest_add_is_refused(luxe):
    with pytest.raises(ValidationError):
        cart_service.guest_add([], luxe.variants.get().pk)


def test_quote_marks_line_unavailable(luxe):
    summary = cart_service.quote([LineInput(luxe.variants.get().pk, 1, 100_00)])
    [line] = summary.lines
    assert line.status == LineStatus.UNAVAILABLE
    assert summary.total_kopecks == 0
    assert not summary.can_checkout


def test_price_removed_after_adding_blocks_checkout_and_keeps_seen_price(customer):
    product = make_product(price_kopecks=1_000_00)
    cart_service.add(customer, product.variants.get().pk)
    Product.objects.filter(pk=product.pk).update(price_kopecks=None)

    summary = cart_service.ack_prices(customer)  # не падает на пустой цене
    assert CartItem.objects.get().seen_price_kopecks == 1_000_00
    assert summary.lines[0].status == LineStatus.UNAVAILABLE
    assert not summary.can_checkout


def test_price_sort_puts_on_request_last(luxe):
    category = luxe.category
    cheap = make_product("Дёшево", category=category, price_kopecks=100_00)
    pricey = make_product("Дорого", category=category, price_kopecks=900_00)
    cases = {Sort.PRICE_ASC: [cheap, pricey, luxe], Sort.PRICE_DESC: [pricey, cheap, luxe]}
    for sort, expected in cases.items():
        found = list(filter_products(ProductFilters(category=category, sort=sort)))
        assert found == expected, sort


def test_price_filter_skips_on_request(luxe):
    found = filter_products(ProductFilters(category=luxe.category, price_min=0))
    assert luxe not in found


def test_public_api_reports_price_on_request(client, luxe):
    data = client.get(f"/api/v1/catalog/products/{luxe.slug}/").json()
    assert data["price_kopecks"] is None
    assert data["price_on_request"] is True
    listed = client.get("/api/v1/catalog/products/").json()["results"]
    assert listed[0]["price_on_request"] is True
