"""Списки панели без N+1: число SQL-запросов не растёт с числом строк на странице.

Сравнивается прогон с одной строкой и с шестью — точное число запросов не фиксируется,
чтобы тест не ломался от безвредных изменений (сессия, права), а ловил именно рост по строкам.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from accounts.models import User
from orders.models import OrderStatus
from orders.tests.factories import make_order
from store.models import ProductStatus
from store.services import catalog

from .conftest import PASSWORD, image_file
from .factories import make_category, make_product

pytestmark = pytest.mark.django_db

ADMIN = "/api/v1/admin"


def queries(client, url: str, params: dict | None = None) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url, params or {})
    assert response.status_code == 200, response.content
    return len(ctx)


def add_products(n: int, **fields) -> None:
    category = make_category()
    status = ProductStatus.objects.get_or_create(name="В наличии")[0]
    for _ in range(n):
        product = make_product(category=category, sizes=("S", "M"), status=status, **fields)
        catalog.add_product_image(product, image_file())


def add_drafts(n: int) -> None:
    add_products(n, is_draft=True, is_active=False)


def add_orders(n: int) -> None:
    for _ in range(n):
        email = f"buyer{User.objects.count()}@example.com"
        customer = User.objects.create_user(email=email, password=PASSWORD)
        make_order(customer, make_product(sizes=("S",)), status=OrderStatus.CONFIRMED)


@pytest.mark.parametrize(
    ("url", "params", "add"),
    [
        (f"{ADMIN}/catalog/products/", {}, lambda n: add_products(n)),
        (f"{ADMIN}/catalog/products/", {"status": "draft"}, lambda n: add_drafts(n)),
        (f"{ADMIN}/catalog/categories/", {}, lambda n: [make_category() for _ in range(n)]),
        (f"{ADMIN}/orders/", {}, add_orders),
        (f"{ADMIN}/customers/", {}, add_orders),
        (f"{ADMIN}/summary/", {}, add_orders),
    ],
    ids=["products", "drafts", "categories", "orders", "customers", "summary"],
)
def test_admin_list_query_count_does_not_grow(admin_client, url, params, add):
    add(1)
    one = queries(admin_client, url, params)
    add(5)
    assert queries(admin_client, url, params) == one


def test_low_stock_in_summary_does_not_grow(admin_client):
    add_products(1, stock=1)
    one = queries(admin_client, f"{ADMIN}/summary/")
    add_products(5, stock=1)
    assert queries(admin_client, f"{ADMIN}/summary/") == one
