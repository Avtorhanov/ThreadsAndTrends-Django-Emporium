"""Онлайн-платежи и возвраты. Источник правды о статусе — API провайдера (ЮKassa):
локальные записи обновляются только сверкой (payments.services.sync_payment / sync_refund)."""

from django.db import models
from django.db.models import Q


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает оплаты"
    SUCCEEDED = "succeeded", "Оплачен"
    CANCELED = "canceled", "Не оплачен"
    REFUNDED = "refunded", "Возвращён"


class RefundStatus(models.TextChoices):
    PENDING = "pending", "Выполняется"
    SUCCEEDED = "succeeded", "Выполнен"
    CANCELED = "canceled", "Отклонён"


class RefundReason(models.TextChoices):
    ORDER_CANCELLED = "order_cancelled", "Заказ отменён"
    LATE_PAYMENT = "late_payment", "Оплата после отмены заказа"
    DUPLICATE_PAYMENT = "duplicate_payment", "Повторная оплата заказа"
    AMOUNT_MISMATCH = "amount_mismatch", "Сумма не совпала с заказом"


class Payment(models.Model):
    # PROTECT: платёж — финансовая история, заказ с платежами не удаляется.
    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="payments", verbose_name="Заказ"
    )
    amount_kopecks = models.PositiveBigIntegerField(verbose_name="Сумма, коп.")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name="Статус",
    )
    # Пусто, пока провайдер не ответил на создание (повтор идёт с тем же idempotency_key).
    provider_payment_id = models.CharField(
        max_length=64, unique=True, null=True, blank=True, verbose_name="ID у провайдера"
    )
    idempotency_key = models.CharField(
        max_length=64, unique=True, verbose_name="Ключ идемпотентности"
    )
    confirmation_url = models.URLField(max_length=2000, blank=True, verbose_name="Страница оплаты")
    cancellation_reason = models.CharField(
        max_length=100, blank=True, verbose_name="Причина отмены у провайдера"
    )
    # Последний ответ провайдера как есть — для разбора спорных случаев.
    payload = models.JSONField(default=dict, blank=True, verbose_name="Ответ провайдера")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="Оплачен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="payment_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_kopecks__gt=0), name="payment_amount_positive"
            ),
            # Одна незавершённая попытка оплаты на заказ: повторное «Оплатить» её переиспользует.
            models.UniqueConstraint(
                fields=["order"],
                condition=Q(status="pending"),
                name="payment_one_pending_per_order",
            ),
        ]

    def __str__(self):
        return f"{self.order} · {self.get_status_display()}"


class Refund(models.Model):
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name="refunds", verbose_name="Платёж"
    )
    amount_kopecks = models.PositiveBigIntegerField(verbose_name="Сумма, коп.")
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        verbose_name="Статус",
    )
    reason = models.CharField(max_length=30, choices=RefundReason.choices, verbose_name="Причина")
    provider_refund_id = models.CharField(
        max_length=64, unique=True, null=True, blank=True, verbose_name="ID у провайдера"
    )
    idempotency_key = models.CharField(
        max_length=64, unique=True, verbose_name="Ключ идемпотентности"
    )
    cancellation_reason = models.CharField(
        max_length=100, blank=True, verbose_name="Причина отказа"
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name="Ответ провайдера")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")

    class Meta:
        verbose_name = "Возврат"
        verbose_name_plural = "Возвраты"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="refund_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(amount_kopecks__gt=0), name="refund_amount_positive"),
            # Только полный возврат: не больше одного выполняющегося или выполненного на платёж.
            models.UniqueConstraint(
                fields=["payment"],
                condition=Q(status__in=["pending", "succeeded"]),
                name="refund_one_active_per_payment",
            ),
        ]

    def __str__(self):
        return f"Возврат {self.payment.order} · {self.get_status_display()}"
