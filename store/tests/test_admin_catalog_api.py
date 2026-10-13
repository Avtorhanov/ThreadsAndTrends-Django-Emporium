import pytest
from rest_framework.test import APIClient

from store.models import Product, ProductImage, ProductVariant

from .conftest import PASSWORD, image_file
from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

BASE = "/api/v1/admin/catalog"
CATEGORIES = f"{BASE}/categories/"
PRODUCTS = f"{BASE}/products/"


# --- Доступ ---


@pytest.mark.parametrize("url", [CATEGORIES, PRODUCTS])
def test_anonymous_gets_401(api_client, url):
    response = api_client.get(url)
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"


@pytest.mark.parametrize("url", [CATEGORIES, PRODUCTS])
def test_customer_session_is_forbidden(customer, url):
    client = APIClient()
    client.force_login(customer)
    assert client.get(url).status_code == 403
    assert client.post(url, {"name": "x"}, format="json").status_code == 403


def test_jwt_is_not_accepted(api_client, staff):
    access = api_client.post(
        "/api/v1/auth/login/", {"email": staff.email, "password": PASSWORD}, format="json"
    ).json()["access"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get(PRODUCTS).status_code == 401


# --- Категории ---


def test_category_crud(admin_client):
    response = admin_client.post(CATEGORIES, {"name": "Одежда"}, format="json")
    assert response.status_code == 201, response.content
    root = response.json()
    assert root["slug"] == "odezhda"
    assert root["parent"] is None

    response = admin_client.post(
        CATEGORIES, {"name": "Футболки", "parent": root["id"], "position": 2}, format="json"
    )
    assert response.status_code == 201
    child = response.json()

    rows = {row["id"]: row for row in admin_client.get(CATEGORIES).json()}
    assert rows[root["id"]]["children_count"] == 1
    assert rows[child["id"]]["parent"] == root["id"]

    response = admin_client.patch(
        f"{CATEGORIES}{child['id']}/", {"is_active": False, "name": "Майки"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["slug"] == "futbolki"

    response = admin_client.delete(f"{CATEGORIES}{root['id']}/")
    assert response.status_code == 400
    assert admin_client.delete(f"{CATEGORIES}{child['id']}/").status_code == 204


def test_category_validation_errors(admin_client):
    root = make_category()
    child = make_category(parent=root)
    response = admin_client.post(
        CATEGORIES, {"name": "Третий уровень", "parent": child.pk}, format="json"
    )
    assert response.status_code == 400
    assert "parent" in response.json()

    response = admin_client.post(CATEGORIES, {"name": "Дубль", "slug": root.slug}, format="json")
    assert response.status_code == 400
    assert "slug" in response.json()


def test_products_count_ignores_deleted(admin_client):
    category = make_category()
    make_product(category=category)
    make_product(category=category, deleted_at="2026-01-01T00:00:00Z")
    row = admin_client.get(f"{CATEGORIES}{category.pk}/").json()
    assert row["products_count"] == 1


# --- Товары ---


def test_create_product_with_variants(admin_client):
    category = make_category()
    payload = {
        "name": "Кроссовки беговые",
        "category": category.pk,
        "price_kopecks": 7_990_00,
        "compare_at_kopecks": 9_990_00,
        "description": "Лёгкие",
        "variants": [{"size": "41", "stock": 2}, {"size": "42", "sku": "RUN-42", "stock": 0}],
    }
    response = admin_client.post(PRODUCTS, payload, format="json")
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["slug"] == "krossovki-begovye"
    assert data["total_stock"] == 2
    assert [(v["size"], v["stock"]) for v in data["variants"]] == [("41", 2), ("42", 0)]
    assert data["variants"][1]["sku"] == "RUN-42"
    assert data["images"] == [] and data["cover_url"] is None


def test_create_product_rejects_bad_money(admin_client):
    category = make_category()
    response = admin_client.post(
        PRODUCTS,
        {"name": "x", "category": category.pk, "price_kopecks": "10.50"},
        format="json",
    )
    assert response.status_code == 400
    assert "price_kopecks" in response.json()

    response = admin_client.post(
        PRODUCTS,
        {"name": "x", "category": category.pk, "price_kopecks": 100, "compare_at_kopecks": 50},
        format="json",
    )
    assert response.status_code == 400
    assert "compare_at_kopecks" in response.json()


def test_product_list_filters(admin_client):
    root = make_category()
    shirts = make_category(parent=root)
    other = make_category()
    in_stock = make_product(name="Футболка", category=shirts, stock=3)
    empty = make_product(name="Майка", category=shirts, stock=0)
    hidden = make_product(name="Скрытая", category=other, is_active=False)
    deleted = make_product(name="Удалённая", category=other, deleted_at="2026-01-01T00:00:00Z")

    def ids(**params):
        response = admin_client.get(PRODUCTS, params)
        assert response.status_code == 200
        return {row["id"] for row in response.json()["results"]}

    assert ids() == {in_stock.pk, empty.pk, hidden.pk}
    assert ids(status="active") == {in_stock.pk, empty.pk}
    assert ids(status="inactive") == {hidden.pk}
    assert ids(status="deleted") == {deleted.pk}
    assert ids(category=root.pk) == {in_stock.pk, empty.pk}
    assert ids(stock="in_stock") == {in_stock.pk, hidden.pk}
    assert ids(stock="out_of_stock") == {empty.pk}
    assert ids(search="футб") == {in_stock.pk}
    sku = in_stock.variants.get().sku
    assert ids(search=sku.lower()) == {in_stock.pk}


def test_product_patch_delete_restore(admin_client):
    product = make_product(price_kopecks=1000)
    url = f"{PRODUCTS}{product.pk}/"

    response = admin_client.patch(url, {"price_kopecks": 1500, "is_active": False}, format="json")
    assert response.status_code == 200
    assert (response.json()["price_kopecks"], response.json()["is_active"]) == (1500, False)

    assert admin_client.delete(url).status_code == 204
    assert Product.all_objects.get(pk=product.pk).deleted_at is not None
    assert admin_client.get(url).json()["deleted_at"] is not None  # админ видит удалённый

    response = admin_client.post(f"{url}restore/")
    assert response.status_code == 200
    assert response.json()["deleted_at"] is None


def test_variants_api(admin_client):
    product = make_product()
    default = product.variants.get()

    response = admin_client.post(f"{PRODUCTS}{product.pk}/variants/", {"size": "M"}, format="json")
    assert response.status_code == 400  # нельзя смешивать «Без размера» и размеры

    response = admin_client.patch(
        f"{BASE}/variants/{default.pk}/", {"size": "S", "stock": 4}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["size"] == "S"

    response = admin_client.post(
        f"{PRODUCTS}{product.pk}/variants/", {"size": "M", "stock": 1}, format="json"
    )
    assert response.status_code == 201
    medium_id = response.json()["id"]

    assert admin_client.delete(f"{BASE}/variants/{medium_id}/").status_code == 204
    assert admin_client.delete(f"{BASE}/variants/{default.pk}/").status_code == 400
    assert ProductVariant.objects.filter(product=product).count() == 1


def test_images_api(admin_client):
    product = make_product()
    url = f"{PRODUCTS}{product.pk}/images/"

    first = admin_client.post(url, {"image": image_file()}, format="multipart")
    assert first.status_code == 201, first.content
    assert first.json()["url"].startswith("http://testserver/")
    second = admin_client.post(url, {"image": image_file("WEBP", "b.webp")}, format="multipart")
    assert second.status_code == 201

    response = admin_client.post(url, {"image": image_file("GIF", "c.gif")}, format="multipart")
    assert response.status_code == 400
    assert "image" in response.json()

    order = [second.json()["id"], first.json()["id"]]
    response = admin_client.post(f"{url}reorder/", {"ids": order}, format="json")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == order

    detail = admin_client.get(f"{PRODUCTS}{product.pk}/").json()
    assert detail["cover_url"] == second.json()["url"]

    assert admin_client.delete(f"{BASE}/images/{first.json()['id']}/").status_code == 204
    assert list(ProductImage.objects.values_list("id", flat=True)) == [second.json()["id"]]
