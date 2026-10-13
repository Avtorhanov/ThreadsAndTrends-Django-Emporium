"""Перенос легаси-данных каталога (store 0002–0004, orders 0002–0004)."""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

OLD = [("store", "0001_initial"), ("orders", "0001_initial")]
# Состояние сразу после переноса каталога (дальше корзину меняет сессия 4).
CATALOG = [("store", "0004_catalog_finalize"), ("orders", "0004_money_kopecks_finalize")]


@pytest.fixture
def migrator(transactional_db):
    executor = MigrationExecutor(connection)
    yield executor
    # Вернуть схему к актуальной для остальных тестов.
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_legacy_catalog_is_converted(migrator):
    migrator.migrate(OLD)
    old = migrator.loader.project_state(OLD).apps

    User = old.get_model("accounts", "User")
    Category = old.get_model("store", "Category")
    SubCategory = old.get_model("store", "SubCategory")
    Product = old.get_model("store", "Product")
    Cart = old.get_model("store", "Cart")
    CartItem = old.get_model("store", "CartItem")
    Order = old.get_model("orders", "Order")
    OrderItem = old.get_model("orders", "OrderItem")

    user = User.objects.create(email="buyer@example.com", password="!")
    clothes = Category.objects.create(name="Одежда")
    shoes = Category.objects.create(name="Обувь")
    shirts = SubCategory.objects.create(name="Футболки", category=clothes)

    def product(name, price, **fields):
        fields.setdefault("image", "")
        return Product.objects.create(name=name, description="", price=Decimal(price), **fields)

    in_sub = product("Футболка", "1990.50", category=clothes, subcategory=shirts, image="p/a.jpg")
    same_name = product("Футболка", "10.00", category=clothes, subcategory=shirts)
    in_root_with_children = product("Шарф", "500.00", category=clothes)
    in_leaf_root = product("Кеды", "3000.00", category=shoes, status="Снято с поставок")
    no_category = product("Без всего", "0.00")

    cart = Cart.objects.create(owner=user)
    CartItem.objects.create(cart=cart, product=in_sub, quantity=1, price=Decimal("1990.50"))
    order = Order.objects.create(owner=user, total_price=Decimal("3981.00"))
    OrderItem.objects.create(order=order, product=in_sub, quantity=2, price=Decimal("1990.50"))

    migrator.loader.build_graph()
    migrator.migrate(CATALOG)
    new = migrator.loader.project_state(CATALOG).apps

    NewCategory = new.get_model("store", "Category")
    NewProduct = new.get_model("store", "Product")
    Variant = new.get_model("store", "ProductVariant")
    Image = new.get_model("store", "ProductImage")

    child = NewCategory.objects.get(name="Футболки")
    assert child.parent_id == clothes.pk
    assert child.slug == "futbolki"
    assert NewCategory.objects.get(pk=clothes.pk).slug == "odezhda"

    converted = {p.pk: p for p in NewProduct.objects.all()}
    assert converted[in_sub.pk].price_kopecks == 199050
    assert converted[in_sub.pk].category_id == child.pk
    assert converted[in_sub.pk].slug == "futbolka"
    assert converted[same_name.pk].slug == "futbolka-2"
    assert converted[in_leaf_root.pk].category_id == shoes.pk
    assert converted[in_leaf_root.pk].is_active is False

    other = NewCategory.objects.get(pk=converted[in_root_with_children.pk].category_id)
    assert (other.name, other.parent_id) == ("Другое", clothes.pk)

    orphan = converted[no_category.pk]
    assert NewCategory.objects.get(pk=orphan.category_id).name == "Без категории"
    assert (orphan.price_kopecks, orphan.is_active) == (1, False)

    variant = Variant.objects.get(product_id=in_sub.pk)
    assert (variant.size, variant.sku, variant.stock) == ("", f"DD-{in_sub.pk:05d}", 0)
    assert Variant.objects.count() == 5
    assert list(Image.objects.values_list("product_id", "image")) == [(in_sub.pk, "p/a.jpg")]

    assert new.get_model("store", "CartItem").objects.get().price_kopecks == 199050
    assert new.get_model("orders", "Order").objects.get().total_kopecks == 398100
    assert new.get_model("orders", "OrderItem").objects.get().price_kopecks == 199050

    # Последовательности сдвинуты после вставок с явными pk.
    assert NewCategory.objects.create(name="Новая", slug="novaya").pk > child.pk
