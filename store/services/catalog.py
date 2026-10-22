"""Управление каталогом (администратор). Не зависит от DRF: ошибки — django ValidationError,
API превращает их в 400."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from core.text import slugify_ru
from store.models import Category, Product, ProductImage, ProductVariant
from store.services.images import delete_thumbnails
from store.tasks import make_image_thumbnails

MAX_PRICE_KOPECKS = 100_000_000_00  # 100 млн ₽ — защита от опечаток при вводе
MAX_IMAGES_PER_PRODUCT = 10
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000  # защита от «декомпрессионных бомб»
IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

CATEGORY_FIELDS = {"name", "slug", "parent", "position", "is_active"}
PRODUCT_FIELDS = {
    "name",
    "slug",
    "description",
    "category",
    "price_kopecks",
    "compare_at_kopecks",
    "is_active",
}
VARIANT_FIELDS = {"size", "sku", "stock", "position"}


# --- Slug ---


def _unique_slug(queryset, value: str, *, fallback: str, max_length: int) -> str:
    base = slugify_ru(value, max_length - 10) or fallback
    slug, n = base, 2
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _check_slug_free(queryset, slug: str, *, exclude_pk=None):
    taken = queryset.filter(slug=slug)
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise ValidationError({"slug": "Такой slug уже занят."})


# --- Категории ---


def _validate_category_tree(category: Category | None, parent: Category | None):
    if parent is None:
        return
    if category is not None and parent.pk == category.pk:
        raise ValidationError({"parent": "Категория не может быть родителем самой себя."})
    if parent.parent_id is not None:
        raise ValidationError({"parent": "Допускается только два уровня категорий."})
    if category is not None and category.children.exists():
        raise ValidationError(
            {"parent": "У категории есть подкатегории — она может быть только корневой."}
        )
    if Product.all_objects.filter(category=parent).exists():
        raise ValidationError(
            {
                "parent": f"В категории «{parent.name}» есть товары: "
                "подкатегории создаются только в категориях без товаров."
            }
        )


@transaction.atomic
def create_category(*, name: str, parent=None, slug: str = "", position=0, is_active=True):
    _validate_category_tree(None, parent)
    if slug:
        _check_slug_free(Category.objects, slug)
    else:
        slug = _unique_slug(Category.objects, name, fallback="category", max_length=120)
    return Category.objects.create(
        name=name, parent=parent, slug=slug, position=position, is_active=is_active
    )


@transaction.atomic
def update_category(category: Category, **changes):
    unknown = set(changes) - CATEGORY_FIELDS
    if unknown:
        raise ValueError(f"Неизвестные поля категории: {sorted(unknown)}")
    if "parent" in changes and changes["parent"] != category.parent:
        _validate_category_tree(category, changes["parent"])
    if changes.get("slug") and changes["slug"] != category.slug:
        _check_slug_free(Category.objects, changes["slug"], exclude_pk=category.pk)
    elif "slug" in changes and not changes["slug"]:
        changes.pop("slug")  # пустой slug не затирает существующий
    for field, value in changes.items():
        setattr(category, field, value)
    category.save()
    return category


@transaction.atomic
def delete_category(category: Category):
    if category.children.exists():
        raise ValidationError("Сначала удалите или перенесите подкатегории.")
    # all_objects: мягко удалённые товары тоже держат категорию (история заказов).
    if Product.all_objects.filter(category=category).exists():
        raise ValidationError(
            "В категории есть товары (в том числе удалённые). Перенесите их или скройте категорию."
        )
    category.delete()


# --- Товары ---


def _validate_product_fields(*, category, price_kopecks, compare_at_kopecks):
    errors = {}
    if category is not None and category.children.exists():
        errors["category"] = "Выберите конечную категорию (без подкатегорий)."
    if not 1 <= price_kopecks <= MAX_PRICE_KOPECKS:
        errors["price_kopecks"] = "Цена должна быть больше нуля и не больше 100 млн ₽."
    if compare_at_kopecks is not None and compare_at_kopecks <= price_kopecks:
        errors["compare_at_kopecks"] = "Старая цена должна быть больше текущей."
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def create_product(
    *,
    name: str,
    category: Category,
    price_kopecks: int,
    description: str = "",
    compare_at_kopecks: int | None = None,
    is_active: bool = True,
    slug: str = "",
    variants: list[dict] | None = None,
) -> Product:
    _validate_product_fields(
        category=category, price_kopecks=price_kopecks, compare_at_kopecks=compare_at_kopecks
    )
    if slug:
        _check_slug_free(Product.all_objects, slug)
    else:
        slug = _unique_slug(Product.all_objects, name, fallback="product", max_length=220)

    product = Product.objects.create(
        name=name,
        slug=slug,
        description=description,
        category=category,
        price_kopecks=price_kopecks,
        compare_at_kopecks=compare_at_kopecks,
        is_active=is_active,
    )
    # Товар без вариантов не продаётся: по умолчанию создаётся «Без размера».
    for variant in variants or [{"size": ""}]:
        create_variant(product, **variant)
    return product


@transaction.atomic
def update_product(product: Product, **changes) -> Product:
    unknown = set(changes) - PRODUCT_FIELDS
    if unknown:
        raise ValueError(f"Неизвестные поля товара: {sorted(unknown)}")
    _validate_product_fields(
        category=changes["category"] if "category" in changes else None,
        price_kopecks=changes.get("price_kopecks", product.price_kopecks),
        compare_at_kopecks=changes.get("compare_at_kopecks", product.compare_at_kopecks),
    )
    if changes.get("slug") and changes["slug"] != product.slug:
        _check_slug_free(Product.all_objects, changes["slug"], exclude_pk=product.pk)
    elif "slug" in changes and not changes["slug"]:
        changes.pop("slug")
    for field, value in changes.items():
        setattr(product, field, value)
    product.save()
    return product


def soft_delete_product(product: Product) -> Product:
    if product.deleted_at is None:
        product.deleted_at = timezone.now()
        product.save(update_fields=["deleted_at", "updated_at"])
    return product


def restore_product(product: Product) -> Product:
    if product.deleted_at is not None:
        product.deleted_at = None
        product.save(update_fields=["deleted_at", "updated_at"])
    return product


# --- Варианты ---


def _lock_product(product: Product) -> Product:
    # Блокировка строки товара сериализует операции над его вариантами и галереей
    # (проверки «последний вариант», «лимит изображений» без гонок).
    return Product.all_objects.select_for_update().get(pk=product.pk)


def _generate_sku(product: Product, size: str) -> str:
    base = f"DD-{product.pk:05d}"
    if size:
        base = f"{base}-{(slugify_ru(size, 20) or 'size').upper()}"
    sku, n = base, 2
    while ProductVariant.objects.filter(sku=sku).exists():
        sku = f"{base}-{n}"
        n += 1
    return sku


def _validate_variant_set(product: Product, *, size: str, sku: str, exclude_pk=None):
    siblings = ProductVariant.objects.filter(product=product)
    if exclude_pk is not None:
        siblings = siblings.exclude(pk=exclude_pk)
    sizes = set(siblings.values_list("size", flat=True))
    if size in sizes:
        raise ValidationError({"size": "Такой размер у товара уже есть."})
    if sizes and ("" in sizes or size == ""):
        raise ValidationError(
            {"size": "Вариант «Без размера» нельзя сочетать с размерами — укажите размер у него."}
        )
    taken = ProductVariant.objects.filter(sku=sku)
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise ValidationError({"sku": "Такой артикул уже используется."})


def _save_variant(variant: ProductVariant):
    try:
        with transaction.atomic():
            variant.save()
    except IntegrityError as exc:
        # Параллельное создание того же размера/артикула упирается в уникальный индекс.
        raise ValidationError("Размер или артикул уже заняты.") from exc
    return variant


@transaction.atomic
def create_variant(
    product: Product, *, size: str = "", sku: str = "", stock: int = 0, position=None
) -> ProductVariant:
    product = _lock_product(product)
    size, sku = size.strip(), sku.strip()
    sku = sku or _generate_sku(product, size)
    _validate_variant_set(product, size=size, sku=sku)
    if position is None:
        last = ProductVariant.objects.filter(product=product).aggregate(m=Max("position"))["m"]
        position = 0 if last is None else last + 1
    return _save_variant(
        ProductVariant(product=product, size=size, sku=sku, stock=stock, position=position)
    )


@transaction.atomic
def update_variant(variant: ProductVariant, **changes) -> ProductVariant:
    unknown = set(changes) - VARIANT_FIELDS
    if unknown:
        raise ValueError(f"Неизвестные поля варианта: {sorted(unknown)}")
    _lock_product(variant.product)
    size = changes.get("size", variant.size).strip()
    sku = changes.get("sku", variant.sku).strip() or variant.sku
    _validate_variant_set(variant.product, size=size, sku=sku, exclude_pk=variant.pk)
    changes.update(size=size, sku=sku)
    for field, value in changes.items():
        setattr(variant, field, value)
    return _save_variant(variant)


@transaction.atomic
def delete_variant(variant: ProductVariant) -> None:
    _lock_product(variant.product)
    if (
        not ProductVariant.objects.filter(product_id=variant.product_id)
        .exclude(pk=variant.pk)
        .exists()
    ):
        raise ValidationError("У товара должен остаться хотя бы один вариант.")
    # Мягкое удаление: вариант может быть в истории заказов (сессия 5).
    variant.deleted_at = timezone.now()
    variant.save(update_fields=["deleted_at", "updated_at"])


# --- Изображения ---


def inspect_image(uploaded) -> str:
    """Проверяет файл и возвращает правильное расширение по фактическому формату.
    Общая проверка фото: товары и статьи (content.services)."""
    if uploaded.size > MAX_IMAGE_BYTES:
        raise ValidationError({"image": "Файл больше 5 МБ."})
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as img:
            image_format = img.format
            width, height = img.size
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError({"image": "Файл не является изображением."}) from exc
    finally:
        uploaded.seek(0)
    if image_format not in IMAGE_FORMATS:
        raise ValidationError({"image": "Допустимые форматы: JPEG, PNG, WebP."})
    if width * height > MAX_IMAGE_PIXELS:
        raise ValidationError({"image": "Слишком большое разрешение изображения."})
    return IMAGE_FORMATS[image_format]


@transaction.atomic
def add_product_image(product: Product, uploaded) -> ProductImage:
    product = _lock_product(product)
    if ProductImage.objects.filter(product=product).count() >= MAX_IMAGES_PER_PRODUCT:
        raise ValidationError({"image": f"Не больше {MAX_IMAGES_PER_PRODUCT} изображений."})
    extension = inspect_image(uploaded)
    # Имя от клиента не доверяем: путь строит product_image_path, расширение — по формату.
    uploaded.name = f"upload{extension}"
    last = ProductImage.objects.filter(product=product).aggregate(m=Max("position"))["m"]
    image = ProductImage.objects.create(
        product=product, image=uploaded, position=0 if last is None else last + 1
    )
    # Уменьшенные копии для витрины — в воркере, после фиксации (файл и запись уже есть).
    transaction.on_commit(lambda: make_image_thumbnails.enqueue(image.pk))
    return image


@transaction.atomic
def delete_product_image(image: ProductImage) -> None:
    storage, name = image.image.storage, image.image.name
    image.delete()
    # Файлы удаляются только после фиксации транзакции: при откате запись и файлы целы.
    transaction.on_commit(lambda: (storage.delete(name), delete_thumbnails(storage, name)))


@transaction.atomic
def reorder_product_images(product: Product, image_ids: list[int]) -> list[ProductImage]:
    product = _lock_product(product)
    images = {image.pk: image for image in ProductImage.objects.filter(product=product)}
    if len(image_ids) != len(set(image_ids)) or set(image_ids) != set(images):
        raise ValidationError({"ids": "Передайте все изображения товара, каждое один раз."})
    ordered = [images[pk] for pk in image_ids]
    for position, image in enumerate(ordered):
        image.position = position
    ProductImage.objects.bulk_update(ordered, ["position"])
    return ordered
