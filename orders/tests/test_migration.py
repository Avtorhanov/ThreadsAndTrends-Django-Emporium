"""Пересоздание заказов (orders 0005): тестовые заказы удаляются, номера идут с DD-100001."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from orders.models import ORDER_NUMBER_SEQUENCE, Order

BEFORE = [("orders", "0004_money_kopecks_finalize"), ("store", "0007_cart_variant_finalize")]


@pytest.fixture
def migrator(transactional_db):
    executor = MigrationExecutor(connection)
    yield executor
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_legacy_orders_are_removed(migrator):
    migrator.migrate(BEFORE)
    old = migrator.loader.project_state(BEFORE).apps
    user = old.get_model("accounts", "User").objects.create(email="old@example.com")
    old.get_model("orders", "Order").objects.create(owner=user, total_kopecks=100_00)

    migrator = MigrationExecutor(connection)
    migrator.migrate(migrator.loader.graph.leaf_nodes())

    assert not Order.objects.exists()
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval(%s)", [ORDER_NUMBER_SEQUENCE])
        assert cursor.fetchone()[0] >= 100001
