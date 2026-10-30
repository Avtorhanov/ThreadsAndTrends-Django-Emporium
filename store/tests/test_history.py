import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts import services as accounts
from store.models import ProductView
from store.services import history, storefront

from .conftest import PASSWORD
from .factories import make_category, make_product

User = get_user_model()


@pytest.fixture
def catalog(db):
    clothes = make_category("Одежда", slug="odezhda")
    tees = make_category("Футболки", parent=clothes, slug="futbolki")
    hoodies = make_category("Худи", parent=clothes, slug="hudi")
    shoes = make_category("Обувь", slug="obuv")
    return {
        "tee": make_product("Футболка", category=tees, slug="tee"),
        "tee_sold": make_product("Футболка без остатка", category=tees, slug="tee-sold", stock=0),
        "tee2": make_product("Футболка 2", category=tees, slug="tee-2"),
        "hoodie": make_product("Худи", category=hoodies, slug="hoodie"),
        "hidden": make_product("Скрытая", category=tees, slug="hidden", is_active=False),
        "shoe": make_product("Кеды", category=shoes, slug="shoe"),
    }


def test_record_view_upserts_and_orders_newest_first(customer, catalog):
    history.record_view(customer, catalog["tee"])
    history.record_view(customer, catalog["shoe"])
    history.record_view(customer, catalog["tee"])
    assert ProductView.objects.filter(user=customer).count() == 2
    assert [p.slug for p in history.recent_products(customer)] == ["tee", "shoe"]


def test_history_is_trimmed(customer, catalog, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_LIMIT", 2)
    for key in ("tee", "tee2", "hoodie"):
        history.record_view(customer, catalog[key])
    assert [p.slug for p in history.recent_products(customer)] == ["hoodie", "tee-2"]


def test_hidden_products_are_skipped_and_staff_not_recorded(customer, staff, catalog):
    history.record_view(customer, catalog["hidden"])
    assert history.recent_products(customer) == []
    history.record_view(staff, catalog["tee"])
    assert not ProductView.objects.filter(user=staff).exists()


def test_account_deletion_clears_history(customer, catalog):
    history.record_view(customer, catalog["tee"])
    accounts.delete_own_account(customer, password=PASSWORD)
    assert not ProductView.objects.filter(user=customer).exists()


def test_similar_same_category_first_in_stock_first(catalog):
    similar = [p.slug for p in storefront.similar_products(catalog["tee"])]
    assert similar == ["tee-2", "tee-sold", "hoodie"]  # без самого товара, скрытого и другого корня


def test_similar_api(api_client, catalog):
    response = api_client.get("/api/v1/catalog/products/tee/similar/")
    assert response.status_code == 200
    assert [p["slug"] for p in response.json()] == ["tee-2", "tee-sold", "hoodie"]
    assert api_client.get("/api/v1/catalog/products/hidden/similar/").status_code == 404


def test_viewed_api(customer, catalog):
    client = APIClient()
    assert client.get("/api/v1/catalog/viewed/").status_code == 401
    client.force_authenticate(customer)
    assert client.post("/api/v1/catalog/viewed/", {"slug": "tee"}, format="json").status_code == 204
    assert (
        client.post("/api/v1/catalog/viewed/", {"slug": "hidden"}, format="json").status_code == 404
    )
    assert [p["slug"] for p in client.get("/api/v1/catalog/viewed/").json()] == ["tee"]
    assert client.delete("/api/v1/catalog/viewed/").status_code == 204
    assert client.get("/api/v1/catalog/viewed/").json() == []
