import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone

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
        return self.annotate(
            total_stock=Sum("variants__stock", filter=Q(variants__deleted_at__isnull=True))
        )


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
    price_kopecks = models.PositiveBigIntegerField(verbose_name="Цена, коп.")
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
        ]
        constraints = [
            models.CheckConstraint(condition=Q(price_kopecks__gt=0), name="product_price_positive"),
            models.CheckConstraint(
                condition=Q(compare_at_kopecks__isnull=True)
                | Q(compare_at_kopecks__gt=F("price_kopecks")),
                name="product_compare_at_gt_price",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

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

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товара"
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.product} #{self.position}"


class Cart(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Покупатель",
    )
    session_key = models.CharField(max_length=32, null=True, blank=True, verbose_name="Гость")
    products = models.ManyToManyField("Product", through="CartItem")

    def __str__(self):
        return f"Козина — {self.owner or self.session_key}"

    def calculate_total_kopecks(self) -> int:
        return sum(
            item.quantity * item.product.price_kopecks
            for item in self.cartitem_set.select_related("product")
        )

    class Meta:
        verbose_name = "Корзину"
        verbose_name_plural = "Корзины"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name="Элемент из корзины")
    # Корзина — не история: CASCADE допустим. Логика корзины переписывается в сессии 4.
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    price_kopecks = models.PositiveBigIntegerField(default=0, verbose_name="Цена, коп.")

    def __str__(self):
        return f"{self.quantity} из {self.product} в корзине"

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_cart_product",
            ),
        ]
