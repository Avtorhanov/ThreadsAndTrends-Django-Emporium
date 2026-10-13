# Сессия 5: новая модель заказов (state machine, снимок позиций, номер из последовательности).
# Существующие заказы тестовые — таблицы пересоздаются, данные удаляются (решение сессии 5).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

SEQUENCE = "orders_order_number_seq"


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_money_kopecks_finalize"),
        ("store", "0007_cart_variant_finalize"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name="OrderItem"),
        migrations.DeleteModel(name="Order"),
        migrations.RunSQL(
            sql=f"CREATE SEQUENCE IF NOT EXISTS {SEQUENCE} START WITH 100001",
            reverse_sql=f"DROP SEQUENCE IF EXISTS {SEQUENCE}",
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "number",
                    models.CharField(
                        editable=False, max_length=20, unique=True, verbose_name="Номер"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("awaiting_payment", "Ожидает оплаты"),
                            ("confirmed", "Принят"),
                            ("paid", "Оплачен"),
                            ("assembled", "Собран"),
                            ("shipped", "Отправлен"),
                            ("ready_for_pickup", "Готов к выдаче"),
                            ("delivered", "Получен"),
                            ("cancelled", "Отменён"),
                        ],
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[("online", "Онлайн"), ("on_delivery", "При получении")],
                        max_length=20,
                        verbose_name="Способ оплаты",
                    ),
                ),
                (
                    "delivery_method",
                    models.CharField(
                        choices=[("courier", "Курьер"), ("pickup", "Самовывоз")],
                        max_length=20,
                        verbose_name="Способ доставки",
                    ),
                ),
                (
                    "items_total_kopecks",
                    models.PositiveBigIntegerField(verbose_name="Товары, коп."),
                ),
                ("delivery_kopecks", models.PositiveBigIntegerField(verbose_name="Доставка, коп.")),
                ("total_kopecks", models.PositiveBigIntegerField(verbose_name="Итого, коп.")),
                ("recipient_name", models.CharField(max_length=150, verbose_name="Получатель")),
                ("recipient_phone", models.CharField(max_length=12, verbose_name="Телефон")),
                (
                    "delivery_address",
                    models.CharField(blank=True, max_length=500, verbose_name="Адрес доставки"),
                ),
                (
                    "comment",
                    models.CharField(blank=True, max_length=500, verbose_name="Комментарий"),
                ),
                (
                    "idempotency_key",
                    models.CharField(max_length=64, verbose_name="Ключ идемпотентности"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Оформлен")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Покупатель",
                    ),
                ),
            ],
            options={
                "verbose_name": "Заказ",
                "verbose_name_plural": "Заказы",
                "ordering": ["-created_at", "-id"],
                "indexes": [
                    models.Index(fields=["owner", "-created_at"], name="order_owner_created_idx"),
                    models.Index(
                        fields=["status", "-created_at"], name="order_status_created_idx"
                    ),
                    models.Index(fields=["-created_at"], name="order_created_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("owner", "idempotency_key"), name="order_unique_idempotency_key"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "total_kopecks",
                                models.F("items_total_kopecks") + models.F("delivery_kopecks"),
                            )
                        ),
                        name="order_total_is_sum",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("items_total_kopecks__gt", 0)),
                        name="order_items_total_positive",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("product_name", models.CharField(max_length=200, verbose_name="Название")),
                ("size", models.CharField(blank=True, max_length=50, verbose_name="Размер")),
                ("sku", models.CharField(max_length=64, verbose_name="Артикул")),
                ("price_kopecks", models.PositiveBigIntegerField(verbose_name="Цена, коп.")),
                ("quantity", models.PositiveIntegerField(verbose_name="Количество")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="store.product",
                        verbose_name="Товар",
                    ),
                ),
                (
                    "variant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="store.productvariant",
                        verbose_name="Вариант",
                    ),
                ),
            ],
            options={
                "verbose_name": "Позиция заказа",
                "verbose_name_plural": "Позиции заказа",
                "ordering": ["id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gte", 1)),
                        name="order_item_quantity_gte_1",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="OrderStatusChange",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "from_status",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("awaiting_payment", "Ожидает оплаты"),
                            ("confirmed", "Принят"),
                            ("paid", "Оплачен"),
                            ("assembled", "Собран"),
                            ("shipped", "Отправлен"),
                            ("ready_for_pickup", "Готов к выдаче"),
                            ("delivered", "Получен"),
                            ("cancelled", "Отменён"),
                        ],
                        max_length=20,
                        verbose_name="Из статуса",
                    ),
                ),
                (
                    "to_status",
                    models.CharField(
                        choices=[
                            ("awaiting_payment", "Ожидает оплаты"),
                            ("confirmed", "Принят"),
                            ("paid", "Оплачен"),
                            ("assembled", "Собран"),
                            ("shipped", "Отправлен"),
                            ("ready_for_pickup", "Готов к выдаче"),
                            ("delivered", "Получен"),
                            ("cancelled", "Отменён"),
                        ],
                        max_length=20,
                        verbose_name="В статус",
                    ),
                ),
                (
                    "changed_by",
                    models.CharField(
                        choices=[
                            ("customer", "Клиент"),
                            ("admin", "Администратор"),
                            ("system", "Система"),
                        ],
                        max_length=10,
                        verbose_name="Кто изменил",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Когда")),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_changes",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Смена статуса",
                "verbose_name_plural": "История статусов",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
