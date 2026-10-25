import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone

from store.search import search_vector

# Глубина дерева категорий: корень → подкатегория. Товары — только в конечных категориях.
MAX_CATEGORY_DEPTH = 2


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название")
    slug = models.SlugField(max_length=120, unique=True, verbose_name="Slug")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительская категория",
    )
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_active = models.BooleanField(default=True, verbose_name="Показывать")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменена")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["position", "name"]

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent_id else self.name


class ProductQuerySet(models.QuerySet):
    def live(self):
        """Видимые на витрине: товар и его категории активны (удалённые отсекает менеджер)."""
        return self.filter(is_active=True, category__is_active=True).filter(
            Q(category__parent__isnull=True) | Q(category__parent__is_active=True)
        )

    def with_stock(self):
        queryset = self.annotate(
            total_stock=Sum("variants__stock", filter=Q(variants__deleted_at__isnull=True))
        )
        # Meta.ordering не применяется к запросам с GROUP BY — без явного порядка
        # пагинация нестабильна.
        return queryset.order_by(*(self.query.order_by or self.model._meta.ordering))


class ProductManager(models.Manager.from_queryset(ProductQuerySet)):
    """Менеджер по умолчанию: без мягко удалённых. История заказов ходит через FK
    (base manager), поэтому удалённый товар в ней остаётся доступен."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название")
    slug = models.SlugField(max_length=220, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name="Категория"
    )
    # NULL — «цена по запросу»: товар не продаётся через корзину, покупатель узнаёт цену
    # у продавца (кнопка «Узнать» → мессенджеры).
    price_kopecks = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name="Цена, коп. (пусто — по запросу)"
    )
    compare_at_kopecks = models.PositiveBigIntegerField(
        null=True, blank=True, verbose_name="Старая цена, коп."
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Удалён")

    objects = ProductManager()
    all_objects = models.Manager.from_queryset(ProductQuerySet)()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["-created_at"], name="product_created_idx"),
            models.Index(fields=["is_active", "deleted_at"], name="product_active_deleted_idx"),
            # Основной запрос витрины: товары категории, новые первыми.
            models.Index(
                fields=["category", "-created_at"],
                name="product_live_category_idx",
                condition=Q(is_active=True, deleted_at__isnull=True),
            ),
            # Полнотекстовый поиск витрины (store.services.storefront).
            GinIndex(search_vector(), name="product_search_idx"),
            # Сортировка и фильтр по цене.
            models.Index(fields=["price_kopecks"], name="product_price_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_kopecks__isnull=True) | Q(price_kopecks__gt=0),
                name="product_price_positive",
            ),
            # Старая цена — только у товара с ценой (сравнение с NULL в CHECK проходит молча).
            models.CheckConstraint(
                condition=Q(compare_at_kopecks__isnull=True)
                | Q(price_kopecks__isnull=False, compare_at_kopecks__gt=F("price_kopecks")),
                name="product_compare_at_gt_price",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def price_on_request(self) -> bool:
        return self.price_kopecks is None

    @property
    def cover(self):
        """Первое изображение галереи; использует prefetch, если он есть."""
        images = list(self.images.all())
        return images[0] if images else None

    @property
    def cover_url(self) -> str:
        cover = self.cover
        return cover.image.url if cover else ""

    @property
    def in_stock(self) -> bool:
        # total_stock — аннотация with_stock() (Sum по пустому набору даёт None).
        if hasattr(self, "total_stock"):
            return (self.total_stock or 0) > 0
        return any(variant.stock > 0 for variant in self.variants.all())


class AliveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class ProductVariant(models.Model):
    """Вариант товара (размер) со своим артикулом и остатком.
    Товар без размеров — один вариант с пустым size («Без размера»)."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name="Товар"
    )
    size = models.CharField(max_length=50, blank=True, verbose_name="Размер")
    sku = models.CharField(max_length=64, verbose_name="Артикул")
    stock = models.PositiveIntegerField(default=0, verbose_name="Остаток")
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Удалён")

    objects = AliveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товара"
        ordering = ["position", "id"]
        constraints = [
            # Удалённые варианты не мешают завести такой же размер или артикул заново.
            models.UniqueConstraint(
                fields=["product", "size"],
                condition=Q(deleted_at__isnull=True),
                name="variant_unique_size_per_product",
            ),
            models.UniqueConstraint(
                fields=["sku"],
                condition=Q(deleted_at__isnull=True),
                name="variant_unique_sku",
            ),
        ]

    def __str__(self):
        return f"{self.product} — {self.size or 'без размера'}"

    @property
    def size_label(self) -> str:
        return self.size or "Без размера"


def product_image_path(instance, filename):
    # Имя файла от клиента не используется: только расширение, сам путь — UUID.
    ext = PurePosixPath(filename).suffix.lower() or ".jpg"
    return f"products/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="Товар"
    )
    image = models.ImageField(upload_to=product_image_path, verbose_name="Изображение")
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Загружено")
    # Заполняет store.services.images после загрузки: размеры оригинала (для width/height
    # в разметке — страница не прыгает) и готовность уменьшенных копий WebP.
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name="Ширина, px")
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name="Высота, px")
    thumbs_ready = models.BooleanField(default=False, verbose_name="Превью готовы")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товара"
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product} #{self.position}"

    @property
    def sources(self) -> list[tuple[str, int]]:
        """(url, ширина) для srcset: уменьшенные копии + оригинал. Без превью — только оригинал."""
        from store.services.images import thumb_sources

        return thumb_sources(self)


class Cart(models.Model):
    """Корзина клиента — одна на пользователя. Гостевая корзина хранится на устройстве
    и переносится сюда при входе (store.services.cart.merge)."""

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="Покупатель",
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина — {self.owner}"


class CartItem(models.Model):
    """Позиция корзины. Цена не хранится: сумма всегда считается от текущей цены товара.
    seen_price_kopecks — цена, которую покупатель видел последней; нужна только для
    предупреждения «цена изменилась» и в расчётах не участвует."""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина"
    )
    # Корзина — не история: при физическом удалении варианта позиция удаляется.
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Вариант товара",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    seen_price_kopecks = models.PositiveBigIntegerField(
        verbose_name="Цена, которую видел покупатель, коп."
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")

    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "variant"], name="cart_item_unique_variant"),
            models.CheckConstraint(condition=Q(quantity__gte=1), name="cart_item_quantity_gte_1"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.variant}"
