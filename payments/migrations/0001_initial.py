# Сессия 6: онлайн-платежи и возвраты.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("orders", "0005_orders_state_machine"),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("amount_kopecks", models.PositiveBigIntegerField(verbose_name="Сумма, коп.")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Ожидает оплаты"),
                            ("succeeded", "Оплачен"),
                            ("canceled", "Не оплачен"),
                            ("refunded", "Возвращён"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                (
                    "provider_payment_id",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        unique=True,
                        verbose_name="ID у провайдера",
                    ),
                ),
                (
                    "idempotency_key",
                    models.CharField(
                        max_length=64, unique=True, verbose_name="Ключ идемпотентности"
                    ),
                ),
                (
                    "confirmation_url",
                    models.URLField(blank=True, max_length=2000, verbose_name="Страница оплаты"),
                ),
                (
                    "cancellation_reason",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Причина отмены у провайдера"
                    ),
                ),
                (
                    "payload",
                    models.JSONField(blank=True, default=dict, verbose_name="Ответ провайдера"),
                ),
                ("paid_at", models.DateTimeField(blank=True, null=True, verbose_name="Оплачен")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="orders.order",
                        verbose_name="Заказ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Платёж",
                "verbose_name_plural": "Платежи",
                "ordering": ["created_at", "id"],
                "indexes": [
                    models.Index(
                        fields=["status", "created_at"], name="payment_status_created_idx"
                    )
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("amount_kopecks__gt", 0)),
                        name="payment_amount_positive",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("status", "pending")),
                        fields=("order",),
                        name="payment_one_pending_per_order",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Refund",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("amount_kopecks", models.PositiveBigIntegerField(verbose_name="Сумма, коп.")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Выполняется"),
                            ("succeeded", "Выполнен"),
                            ("canceled", "Отклонён"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Статус",
                    ),
                ),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("order_cancelled", "Заказ отменён"),
                            ("late_payment", "Оплата после отмены заказа"),
                            ("duplicate_payment", "Повторная оплата заказа"),
                            ("amount_mismatch", "Сумма не совпала с заказом"),
                        ],
                        max_length=30,
                        verbose_name="Причина",
                    ),
                ),
                (
                    "provider_refund_id",
                    models.CharField(
                        blank=True,
                        max_length=64,
                        null=True,
                        unique=True,
                        verbose_name="ID у провайдера",
                    ),
                ),
                (
                    "idempotency_key",
                    models.CharField(
                        max_length=64, unique=True, verbose_name="Ключ идемпотентности"
                    ),
                ),
                (
                    "cancellation_reason",
                    models.CharField(blank=True, max_length=100, verbose_name="Причина отказа"),
                ),
                (
                    "payload",
                    models.JSONField(blank=True, default=dict, verbose_name="Ответ провайдера"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Изменён")),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refunds",
                        to="payments.payment",
                        verbose_name="Платёж",
                    ),
                ),
            ],
            options={
                "verbose_name": "Возврат",
                "verbose_name_plural": "Возвраты",
                "ordering": ["created_at", "id"],
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="refund_status_created_idx")
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("amount_kopecks__gt", 0)),
                        name="refund_amount_positive",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("status__in", ["pending", "succeeded"])),
                        fields=("payment",),
                        name="refund_one_active_per_payment",
                    ),
                ],
            },
        ),
    ]
