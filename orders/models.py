"""Заказы. Логика оформления и смены статусов — orders.services; модели хранят данные
и инварианты, которые проверяет БД."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

# Номер заказа берётся из последовательности Postgres (без гонки max+1), см. миграцию 0005.
ORDER_NUMBER_SEQUENCE = "orders_order_number_seq"
ORDER_NUMBER_PREFIX = "DD-"


class OrderStatus(models.TextChoices):
    AWAITING_PAYMENT = "awaiting_payment", "Ожидает оплаты"
    CONFIRMED = "confirmed", "Принят"
    PAID = "paid", "Оплачен"
    ASSEMBLED = "assembled", "Собран"
    SHIPPED = "shipped", "Отправлен"
    READY_FOR_PICKUP = "ready_for_pickup", "Готов к выдаче"
    DELIVERED = "delivered", "Получен"
    CANCELLED = "cancelled", "Отменён"


class PaymentMethod(models.TextChoices):
    ONLINE = "online", "Онлайн"
    ON_DELIVERY = "on_delivery", "При получении"


class DeliveryMethod(models.TextChoices):
    COURIER = "courier", "Курьер"
    PICKUP = "pickup", "Самовывоз"


class ChangedBy(models.TextChoices):
    CUSTOMER = "customer", "Клиент"
    ADMIN = "admin", "Администратор"
    SYSTEM = "system", "Система"


# Конечные статусы: из них переходов нет.
FINAL_STATUSES = (OrderStatus.DELIVERED, OrderStatus.CANCELLED)


class OrderQuerySet(models.QuerySet):
    def unfinished(self):
        return self.exclude(status__in=FINAL_STATUSES)


class Order(models.Model):
    # PROTECT: пользователи удаляются мягко, история заказов не теряется.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Покупатель",
    )
    number = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Номер")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, verbose_name="Статус")
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, verbose_name="Способ оплаты"
    )
    delivery_method = models.CharField(
        max_length=20, choices=DeliveryMethod.choices, verbose_name="Способ доставки"
    )
    items_total_kopecks = models.PositiveBigIntegerField(verbose_name="Товары, коп.")
    delivery_kopecks = models.PositiveBigIntegerField(verbose_name="Доставка, коп.")
    total_kopecks = models.PositiveBigIntegerField(verbose_name="Итого, коп.")
    # Снимок получателя: обезличивается при удалении аккаунта (orders.signals).
    recipient_name = models.CharField(max_length=150, verbose_name="Получатель")
    recipient_phone = models.CharField(max_length=12, verbose_name="Телефон")
    delivery_address = models.CharField(max_length=500, blank=True, verbose_name="Адрес доставки")
    comment = models.CharField(max_length=500, blank=True, verbose_name="Комментарий")
    # Ключ повторного сабмита от клиента: повтор с тем же ключом возвращает тот же заказ.
    idempotency_key = models.CharField(max_length=64, verbose_name="Ключ идемпотентности")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Оформлен")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "-created_at"], name="order_owner_created_idx"),
            models.Index(fields=["status", "-created_at"], name="order_status_created_idx"),
            models.Index(fields=["-created_at"], name="order_created_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "idempotency_key"], name="order_unique_idempotency_key"
            ),
            models.CheckConstraint(
                condition=Q(total_kopecks=F("items_total_kopecks") + F("delivery_kopecks")),
                name="order_total_is_sum",
            ),
            models.CheckConstraint(
                condition=Q(items_total_kopecks__gt=0), name="order_items_total_positive"
            ),
        ]

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    """Позиция заказа: ссылка на вариант и снимок того, что купили и почём."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ"
    )
    # PROTECT: товары и варианты удаляются мягко, история заказов не теряется.
    product = models.ForeignKey(
        "store.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Товар",
    )
    variant = models.ForeignKey(
        "store.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Вариант",
    )
    product_name = models.CharField(max_length=200, verbose_name="Название")
    size = models.CharField(max_length=50, blank=True, verbose_name="Размер")
    sku = models.CharField(max_length=64, verbose_name="Артикул")
    # Снимок статуса товара («Под заказ») на момент заказа: справочник могут поменять.
    status_name = models.CharField(max_length=40, blank=True, verbose_name="Статус товара")
    price_kopecks = models.PositiveBigIntegerField(verbose_name="Цена, коп.")
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="order_item_quantity_gte_1"),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total_kopecks(self) -> int:
        return self.price_kopecks * self.quantity


class OrderStatusChange(models.Model):
    """История статусов. Первая запись (from_status="") — оформление заказа."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="status_changes", verbose_name="Заказ"
    )
    from_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, blank=True, verbose_name="Из статуса"
    )
    to_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, verbose_name="В статус"
    )
    changed_by = models.CharField(
        max_length=10, choices=ChangedBy.choices, verbose_name="Кто изменил"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Пользователь",
    )
    comment = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Комментарий для клиента",
        help_text="Видит клиент в истории заказа и в письме",
    )
    notified = models.BooleanField(default=False, verbose_name="Клиенту отправлено письмо")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Когда")

    class Meta:
        verbose_name = "Смена статуса"
        verbose_name_plural = "История статусов"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.order}: {self.from_status or '—'} → {self.to_status}"
