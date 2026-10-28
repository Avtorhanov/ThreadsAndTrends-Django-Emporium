"""Статусы товаров («Под заказ»…): справочник, метка, массовые действия, показ покупателю."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from store.models import Product, ProductStatus
from store.services import catalog
from store.services.cart import LineInput, quote

from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/admin/catalog/products/"
STATUSES = "/api/v1/admin/catalog/statuses/"


def test_initial_statuses_created_by_migration():
    names = list(ProductStatus.objects.values_list("name", flat=True))
    assert names[:3] == ["В наличии", "Под заказ", "Ожидается поставка"]


def test_status_name_unique_case_insensitive():
    catalog.create_status(name="Предзаказ")
    with pytest.raises(ValidationError):
        catalog.create_status(name="  предзаказ ")


def test_deleting_status_clears_label():
    label = catalog.create_status(name="Распродажа", tone="info")
    product = make_product(status=label)
    catalog.delete_status(label)
    product.refresh_from_db()
    assert product.status is None


def test_bulk_update_status_category_visibility():
    old = make_category("Старая", slug="old")
    new = make_category("Новая", slug="new")
    first, second = make_product(category=old), make_product(category=old)
    untouched = make_product(category=old)
    label = ProductStatus.objects.get(name="Под заказ")

    assert catalog.bulk_update_products([first.pk, second.pk], status=label) == 2
    assert catalog.bulk_update_products([first.pk, second.pk], category=new, is_active=False) == 2
    for product in (first, second):
        product.refresh_from_db()
        assert (product.status, product.category, product.is_active) == (label, new, False)
    untouched.refresh_from_db()
    assert untouched.status is None and untouched.category == old and untouched.is_active


def test_bulk_rejects_category_with_children_and_empty_selection():
    parent = make_category("Одежда", slug="clothes")
    make_category("Футболки", parent=parent, slug="tees")
    product = make_product()
    with pytest.raises(ValidationError):
        catalog.bulk_update_products([product.pk], category=parent)
    with pytest.raises(ValidationError):
        catalog.bulk_update_products([], is_active=False)


# --- API панели ---


def test_admin_statuses_crud(admin_client):
    listed = admin_client.get(STATUSES).json()
    assert {"В наличии", "Под заказ"} <= {item["name"] for item in listed}

    created = admin_client.post(STATUSES, {"name": "Новинка", "tone": "success"}, format="json")
    assert created.status_code == 201, created.content
    pk = created.json()["id"]
    renamed = admin_client.patch(f"{STATUSES}{pk}/", {"hint": "Только что привезли"}, format="json")
    assert renamed.status_code == 200 and renamed.json()["hint"] == "Только что привезли"
    assert admin_client.delete(f"{STATUSES}{pk}/").status_code == 204


def test_admin_bulk_and_label_filter(admin_client):
    first, second = make_product(), make_product()
    label = ProductStatus.objects.get(name="Ожидается поставка")
    response = admin_client.post(
        f"{PRODUCTS}bulk/", {"ids": [first.pk, second.pk], "status": label.pk}, format="json"
    )
    assert response.status_code == 200 and response.json() == {"updated": 2}

    rows = admin_client.get(PRODUCTS, {"label": label.pk}).json()["results"]
    assert {row["id"] for row in rows} == {first.pk, second.pk}
    assert all(row["status"] == label.pk for row in rows)

    body = {"ids": [first.pk], "status": None}
    cleared = admin_client.post(f"{PRODUCTS}bulk/", body, format="json")
    assert cleared.status_code == 200
    assert Product.objects.get(pk=first.pk).status is None


def test_admin_api_rejects_customer(api_client, customer):
    api_client.force_login(customer)
    assert api_client.get(STATUSES).status_code == 403
    body = {"ids": [1], "is_active": False}
    assert api_client.post(f"{PRODUCTS}bulk/", body, format="json").status_code == 403


def test_product_update_sets_status(admin_client):
    product = make_product()
    label = ProductStatus.objects.get(name="Под заказ")
    response = admin_client.patch(f"{PRODUCTS}{product.pk}/", {"status": label.pk}, format="json")
    assert response.status_code == 200 and response.json()["status"] == label.pk


# --- Покупатель ---


def test_public_api_and_cart_show_status(api_client):
    label = ProductStatus.objects.get(name="Под заказ")
    product = make_product(status=label)
    detail = api_client.get(f"/api/v1/catalog/products/{product.slug}/").json()
    expected = {"id": label.pk, "name": "Под заказ", "hint": label.hint, "tone": "warning"}
    assert detail["status"] == expected

    summary = quote([LineInput(variant_id=product.variants.first().pk, quantity=1)])
    assert summary.lines[0].product.status == label


def test_storefront_card_quiet_mark_and_product_pill(client):
    label = ProductStatus.objects.get(name="Под заказ")
    product = make_product("Термос", status=label)
    grid = client.get(reverse("web:home")).content.decode()
    assert 'class="mark mark--warning">Под заказ<' in grid
    page = client.get(reverse("web:product", args=[product.slug])).content.decode()
    assert "status--warning pd__status" in page
