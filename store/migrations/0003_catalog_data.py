# Сессия 3, шаг 2 из 3: перенос данных в новую модель каталога.
#  - SubCategory → дочерние Category (pk = max(pk корней) + pk подкатегории);
#  - цена → копейки; статус «Снято с поставок» → is_active=False;
#  - у каждого товара — вариант «Без размера» (артикул DD-<pk>, остаток 0: реальные
#    остатки заводит администратор), изображение → первая картинка галереи;
#  - снимок цены в корзине → копейки.

from decimal import ROUND_HALF_UP, Decimal

from django.core.management.color import no_style
from django.db import migrations

from core.text import slugify_ru


def to_kopecks(value) -> int:
    if value is None:
        return 0
    return int((Decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))


class SlugPool:
    def __init__(self):
        self.used = set()

    def take(self, name, fallback, max_length):
        base = slugify_ru(name, max_length - 10) or fallback
        slug, n = base, 2
        while slug in self.used:
            slug = f"{base}-{n}"
            n += 1
        self.used.add(slug)
        return slug


def reset_sequences(schema_editor, models):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), models):
            cursor.execute(sql)


def forwards(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    SubCategory = apps.get_model("store", "SubCategory")
    Product = apps.get_model("store", "Product")
    ProductVariant = apps.get_model("store", "ProductVariant")
    ProductImage = apps.get_model("store", "ProductImage")
    CartItem = apps.get_model("store", "CartItem")

    category_slugs = SlugPool()
    roots = list(Category.objects.order_by("pk"))
    for root in roots:
        root.slug = category_slugs.take(root.name, f"category-{root.pk}", 120)
        root.save(update_fields=["slug"])

    offset = max((root.pk for root in roots), default=0)
    child_by_subcategory = {}
    for sub in SubCategory.objects.order_by("pk"):
        child = Category.objects.create(
            pk=offset + sub.pk,
            name=sub.name,
            parent_id=sub.category_id,
            slug=category_slugs.take(sub.name, f"category-{offset + sub.pk}", 120),
        )
        child_by_subcategory[sub.pk] = child.pk
    reset_sequences(schema_editor, [Category])

    roots_with_children = set(
        Category.objects.filter(parent__isnull=False).values_list("parent_id", flat=True)
    )
    fallback = {}

    def fallback_category(parent_id):
        # Товар без категории или лежащий в корне, у которого есть подкатегории:
        # товары допускаются только в конечных категориях.
        if parent_id not in fallback:
            name = "Другое" if parent_id else "Без категории"
            fallback[parent_id] = Category.objects.create(
                name=name,
                parent_id=parent_id,
                slug=category_slugs.take(name, f"category-other-{parent_id or 0}", 120),
            ).pk
        return fallback[parent_id]

    product_slugs = SlugPool()
    variants, images = [], []
    for product in Product.objects.order_by("pk"):
        if product.subcategory_id:
            product.category_id = child_by_subcategory[product.subcategory_id]
        elif product.category_id is None:
            product.category_id = fallback_category(None)
        elif product.category_id in roots_with_children:
            product.category_id = fallback_category(product.category_id)

        product.slug = product_slugs.take(product.name, f"product-{product.pk}", 220)
        product.price_kopecks = to_kopecks(product.price)
        product.is_active = product.status != "Снято с поставок"
        if product.price_kopecks <= 0:
            # Нулевая цена недопустима: товар скрывается до исправления администратором.
            product.price_kopecks = 1
            product.is_active = False
        product.save(
            update_fields=["category", "slug", "price_kopecks", "is_active", "updated_at"]
        )

        variants.append(
            ProductVariant(pk=product.pk, product=product, size="", sku=f"DD-{product.pk:05d}")
        )
        if product.image:
            images.append(ProductImage(product=product, image=product.image.name, position=0))

    ProductVariant.objects.bulk_create(variants)
    ProductImage.objects.bulk_create(images)
    reset_sequences(schema_editor, [ProductVariant])

    for item in CartItem.objects.all():
        item.price_kopecks = to_kopecks(item.price)
        item.save(update_fields=["price_kopecks"])


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0002_catalog_schema"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
