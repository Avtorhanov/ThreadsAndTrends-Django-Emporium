"""Перенос корзин на варианты (store 0005–0007)."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

BEFORE = [("store", "0004_catalog_finalize")]
AFTER = [("store", "0007_cart_variant_finalize")]


@pytest.fixture
def migrator(transactional_db):
    executor = MigrationExecutor(connection)
    yield executor
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_cart_items_move_to_variants(migrator):
    migrator.migrate(BEFORE)
    old = migrator.loader.project_state(BEFORE).apps

    User = old.get_model("accounts", "User")
    Category = old.get_model("store", "Category")
    Product = old.get_model("store", "Product")
    Variant = old.get_model("store", "ProductVariant")
    Cart = old.get_model("store", "Cart")
    CartItem = old.get_model("store", "CartItem")

    category = Category.objects.create(name="Одежда", slug="odezhda")

    def product(slug, sizes, **fields):
        item = Product.objects.create(
            name=slug, slug=slug, category=category, price_kopecks=500_00, **fields
        )
        for size in sizes:
            Variant.objects.create(product=item, size=size, sku=f"{slug}-{size}", stock=3)
        return item

    single = product("single", [""])
    sized = product("sized", ["S", "M"])
    no_variants = product("empty", [])

    user = User.objects.create(email="u@example.com")
    cart = Cart.objects.create(owner=user)
    duplicate = Cart.objects.create(owner=user)
    guest = Cart.objects.create(session_key="abc")
    CartItem.objects.create(cart=cart, product=single, quantity=2, price_kopecks=1)
    CartItem.objects.create(cart=cart, product=sized, quantity=1, price_kopecks=1)
    CartItem.objects.create(cart=cart, product=no_variants, quantity=1, price_kopecks=1)
    CartItem.objects.create(cart=duplicate, product=single, quantity=1, price_kopecks=1)
    CartItem.objects.create(cart=guest, product=single, quantity=1, price_kopecks=1)

    migrator.loader.build_graph()
    migrator.migrate(AFTER)
    new = migrator.loader.project_state(AFTER).apps

    NewCart = new.get_model("store", "Cart")
    NewItem = new.get_model("store", "CartItem")
    assert list(NewCart.objects.values_list("pk", flat=True)) == [cart.pk]
    item = NewItem.objects.get()
    assert (item.cart_id, item.variant.size, item.quantity, item.seen_price_kopecks) == (
        cart.pk,
        "",
        2,
        500_00,
    )
    assert item.variant.product_id == single.pk
