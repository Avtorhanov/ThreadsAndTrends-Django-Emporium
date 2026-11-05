"""Черновики товаров («Товары → Добавить пачкой»): создание, список, публикация."""

import pytest
from django.db import IntegrityError, transaction

from store.models import Product
from store.services import catalog

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/admin/catalog/products/"


def _create_draft(client, category, **extra):
    body = {
        "name": "Пижамы 15",
        "category": category.pk,
        "price_kopecks": None,
        "is_draft": True,
        "is_active": True,  # игнорируется: черновик всегда скрыт
        "variants": [{"size": size, "stock": 0} for size in ("S", "M", "L", "XL")],
        **extra,
    }
    response = client.post(PRODUCTS, body, format="json")
    assert response.status_code == 201, response.content
    return response.json()


def test_create_draft_is_hidden_with_sizes(admin_client):
    data = _create_draft(admin_client, make_category())
    assert (data["is_draft"], data["is_active"], data["price_kopecks"]) == (True, False, None)
    assert [(v["size"], v["stock"]) for v in data["variants"]] == [
        ("S", 0),
        ("M", 0),
        ("L", 0),
        ("XL", 0),
    ]
    assert not Product.objects.live().filter(pk=data["id"]).exists()


def test_drafts_listed_separately(admin_client):
    category = make_category()
    draft = _create_draft(admin_client, category)
    hidden = make_product(category=category, is_active=False)
    active = make_product(category=category)

    def ids(query=""):
        return {row["id"] for row in admin_client.get(PRODUCTS + query).json()["results"]}

    assert ids() == {hidden.pk, active.pk}
    assert ids("?status=inactive") == {hidden.pk}
    assert ids("?status=draft") == {draft["id"]}


def test_patch_is_active_publishes_draft(admin_client):
    data = _create_draft(admin_client, make_category(), price_kopecks=2490_00)
    response = admin_client.patch(f"{PRODUCTS}{data['id']}/", {"is_active": True}, format="json")
    assert response.status_code == 200
    assert (response.json()["is_draft"], response.json()["is_active"]) == (False, True)


def test_patch_without_publishing_keeps_draft(admin_client):
    data = _create_draft(admin_client, make_category())
    changes = {"name": "Пижама в клетку", "price_kopecks": 1990_00}
    response = admin_client.patch(f"{PRODUCTS}{data['id']}/", changes, format="json")
    assert (response.json()["is_draft"], response.json()["is_active"]) == (True, False)


def test_bulk_publish_drafts(admin_client):
    category = make_category()
    first = _create_draft(admin_client, category, price_kopecks=1000_00)
    second = _create_draft(admin_client, category, price_kopecks=2000_00)
    response = admin_client.post(
        f"{PRODUCTS}bulk/", {"ids": [first["id"], second["id"]], "is_active": True}, format="json"
    )
    assert response.json() == {"updated": 2}
    assert not Product.objects.filter(is_draft=True).exists()
    assert Product.objects.live().count() == 2


def test_bulk_category_keeps_draft(admin_client):
    data = _create_draft(admin_client, make_category())
    other = make_category()
    body = {"ids": [data["id"]], "category": other.pk}
    admin_client.post(f"{PRODUCTS}bulk/", body, format="json")
    product = Product.objects.get(pk=data["id"])
    assert (product.category_id, product.is_draft, product.is_active) == (other.pk, True, False)


def test_bulk_hide_does_not_turn_product_into_draft(admin_client):
    product = make_product()
    admin_client.post(f"{PRODUCTS}bulk/", {"ids": [product.pk], "is_active": False}, format="json")
    product.refresh_from_db()
    assert (product.is_active, product.is_draft) == (False, False)


def test_service_draft_ignores_is_active():
    product = catalog.create_product(
        name="Халаты 7", category=make_category(), price_kopecks=None, is_draft=True, is_active=True
    )
    assert (product.is_draft, product.is_active) == (True, False)


def test_db_forbids_visible_draft():
    product = make_product()
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(is_draft=True)


def test_customer_cannot_see_draft(api_client, admin_client):
    data = _create_draft(admin_client, make_category(), price_kopecks=1000_00)
    response = api_client.get(f"/api/v1/catalog/products/{data['slug']}/")
    assert response.status_code == 404
