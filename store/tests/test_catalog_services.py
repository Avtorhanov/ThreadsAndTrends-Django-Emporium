import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from orders.models import Order, OrderItem
from store.models import Category, Product, ProductImage, ProductVariant
from store.services import catalog
from store.templatetags.money import format_kopecks

from .conftest import image_file
from .factories import make_category, make_product

pytestmark = pytest.mark.django_db


# --- Категории ---


def test_category_slug_is_transliterated_and_unique():
    first = catalog.create_category(name="Женская одежда")
    second = catalog.create_category(name="Женская одежда")
    assert first.slug == "zhenskaya-odezhda"
    assert second.slug == "zhenskaya-odezhda-2"


def test_category_tree_is_limited_to_two_levels():
    root = catalog.create_category(name="Одежда")
    child = catalog.create_category(name="Футболки", parent=root)
    with pytest.raises(ValidationError) as exc:
        catalog.create_category(name="Белые", parent=child)
    assert "parent" in exc.value.message_dict


def test_category_with_children_cannot_become_child():
    root = catalog.create_category(name="Одежда")
    catalog.create_category(name="Футболки", parent=root)
    other = catalog.create_category(name="Обувь")
    with pytest.raises(ValidationError):
        catalog.update_category(root, parent=other)
    with pytest.raises(ValidationError):
        catalog.update_category(other, parent=other)


def test_subcategory_cannot_be_created_in_category_with_products():
    category = make_category()
    make_product(category=category)
    with pytest.raises(ValidationError) as exc:
        catalog.create_category(name="Подкатегория", parent=category)
    assert "есть товары" in exc.value.message_dict["parent"][0]


def test_category_rename_keeps_slug():
    category = catalog.create_category(name="Обувь")
    catalog.update_category(category, name="Обувь и аксессуары", slug="")
    category.refresh_from_db()
    assert category.slug == "obuv"


def test_delete_category_protected_by_deleted_products_and_children():
    root = make_category()
    child = make_category(parent=root)
    with pytest.raises(ValidationError):
        catalog.delete_category(root)

    product = make_product(category=child)
    catalog.soft_delete_product(product)
    with pytest.raises(ValidationError):
        catalog.delete_category(child)

    empty = make_category()
    catalog.delete_category(empty)
    assert not Category.objects.filter(pk=empty.pk).exists()


# --- Товары ---


def test_create_product_defaults():
    product = catalog.create_product(
        name="Футболка белая", category=make_category(), price_kopecks=1_990_00
    )
    assert product.slug == "futbolka-belaya"
    assert [(v.size, v.sku, v.stock) for v in product.variants.all()] == [
        ("", f"DD-{product.pk:05d}", 0)
    ]
    assert product.in_stock is False


def test_product_slug_unique_even_against_deleted_products():
    category = make_category()
    first = catalog.create_product(name="Кеды", category=category, price_kopecks=100)
    catalog.soft_delete_product(first)
    second = catalog.create_product(name="Кеды", category=category, price_kopecks=100)
    assert second.slug == "kedy-2"
    with pytest.raises(ValidationError):
        catalog.update_product(second, slug="kedy")


def test_product_requires_leaf_category():
    root = make_category()
    make_category(parent=root)
    with pytest.raises(ValidationError) as exc:
        catalog.create_product(name="Товар", category=root, price_kopecks=100)
    assert "category" in exc.value.message_dict


@pytest.mark.parametrize(
    ("price", "compare_at", "field"),
    [(0, None, "price_kopecks"), (500, 500, "compare_at_kopecks"), (500, 400, "compare_at_kopecks")],
)
def test_product_price_validation(price, compare_at, field):
    with pytest.raises(ValidationError) as exc:
        catalog.create_product(
            name="Товар", category=make_category(), price_kopecks=price, compare_at_kopecks=compare_at
        )
    assert field in exc.value.message_dict


def test_update_product_validates_price_against_existing_compare_at():
    product = make_product(price_kopecks=1000, compare_at_kopecks=1500)
    with pytest.raises(ValidationError):
        catalog.update_product(product, price_kopecks=1500)
    catalog.update_product(product, price_kopecks=1200, compare_at_kopecks=None)
    product.refresh_from_db()
    assert (product.price_kopecks, product.compare_at_kopecks) == (1200, None)


def test_db_constraints_protect_money_invariants():
    product = make_product(price_kopecks=1000)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.all_objects.filter(pk=product.pk).update(price_kopecks=0)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.all_objects.filter(pk=product.pk).update(compare_at_kopecks=1000)


def test_soft_deleted_product_hidden_but_kept_in_order_history(customer):
    product = make_product()
    order = Order.objects.create(owner=customer, total_kopecks=product.price_kopecks)
    item = OrderItem.objects.create(
        order=order, product=product, quantity=1, price_kopecks=product.price_kopecks
    )

    catalog.soft_delete_product(product)

    assert not Product.objects.filter(pk=product.pk).exists()
    assert Product.all_objects.filter(pk=product.pk).exists()
    item = OrderItem.objects.select_related("product").get(pk=item.pk)
    assert item.product.name == product.name  # FK идёт через base manager

    with pytest.raises(ProtectedError):
        Product.all_objects.get(pk=product.pk).delete()

    catalog.restore_product(product)
    assert Product.objects.filter(pk=product.pk).exists()


def test_live_excludes_inactive_product_and_hidden_categories():
    root = make_category()
    child = make_category(parent=root)
    visible = make_product(category=child)
    make_product(category=child, is_active=False)
    assert list(Product.objects.live()) == [visible]

    root.is_active = False
    root.save()
    assert not Product.objects.live().exists()


# --- Варианты ---


def test_variant_rules():
    product = make_product(stock=0)
    default = product.variants.get()

    with pytest.raises(ValidationError):
        catalog.create_variant(product, size="M")  # «Без размера» + размер

    catalog.update_variant(default, size="S", stock=3)
    medium = catalog.create_variant(product, size="M", stock=1)
    assert medium.sku == f"DD-{product.pk:05d}-M"
    assert medium.position == 1

    with pytest.raises(ValidationError):
        catalog.create_variant(product, size="M")
    with pytest.raises(ValidationError):
        catalog.create_variant(product, size="L", sku=medium.sku)

    catalog.delete_variant(medium)
    assert ProductVariant.all_objects.get(pk=medium.pk).deleted_at is not None
    # Удалённый вариант освобождает размер и артикул.
    again = catalog.create_variant(product, size="M", sku=medium.sku)
    assert again.pk != medium.pk

    catalog.delete_variant(again)
    default.refresh_from_db()
    with pytest.raises(ValidationError):
        catalog.delete_variant(default)  # последний вариант


def test_in_stock_ignores_deleted_variants():
    product = make_product(sizes=("S", "M"), stock=0)
    _small, medium = product.variants.all()
    catalog.update_variant(medium, stock=5)
    assert Product.objects.with_stock().get(pk=product.pk).in_stock is True
    catalog.delete_variant(medium)
    assert Product.objects.with_stock().get(pk=product.pk).in_stock is False
    assert Product.objects.get(pk=product.pk).in_stock is False


# --- Изображения ---


def test_image_upload_validation_and_order():
    product = make_product()
    first = catalog.add_product_image(product, image_file("PNG", "../../evil.php"))
    second = catalog.add_product_image(product, image_file("JPEG", "photo.jpeg"))

    assert first.image.name.startswith("products/") and first.image.name.endswith(".png")
    assert second.image.name.endswith(".jpg")
    assert (first.position, second.position) == (0, 1)
    assert product.cover == first

    catalog.reorder_product_images(product, [second.pk, first.pk])
    assert Product.objects.get(pk=product.pk).cover == second
    with pytest.raises(ValidationError):
        catalog.reorder_product_images(product, [second.pk])

    catalog.delete_product_image(first)
    assert list(ProductImage.objects.filter(product=product)) == [second]


@pytest.mark.parametrize(
    "upload",
    [
        lambda: image_file("GIF", "anim.gif"),
        lambda: SimpleUploadedFile("x.png", b"not an image"),
    ],
)
def test_image_rejects_wrong_format(upload):
    with pytest.raises(ValidationError) as exc:
        catalog.add_product_image(make_product(), upload())
    assert "image" in exc.value.message_dict


def test_image_size_and_count_limits(monkeypatch):
    product = make_product()
    big = image_file()
    big.size = catalog.MAX_IMAGE_BYTES + 1
    with pytest.raises(ValidationError):
        catalog.add_product_image(product, big)

    monkeypatch.setattr(catalog, "MAX_IMAGES_PER_PRODUCT", 2)
    catalog.add_product_image(product, image_file())
    catalog.add_product_image(product, image_file())
    with pytest.raises(ValidationError):
        catalog.add_product_image(product, image_file())


# --- Форматирование ---


@pytest.mark.parametrize(
    ("kopecks", "expected"),
    [(0, "0"), (5_500_000, "55 000"), (123_450, "1 234,50"), (5, "0,05")],
)
def test_format_kopecks(kopecks, expected):
    assert format_kopecks(kopecks) == expected
