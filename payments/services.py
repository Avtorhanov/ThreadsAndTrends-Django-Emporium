"""Онлайн-оплата заказа и возвраты.

Правила:
- статус платежа берётся только из API провайдера: тело webhook, ответ приложения и параметры
  возврата со страницы оплаты не доверяются (webhook лишь повод перезапросить платёж);
- сетевые вызовы — вне транзакций БД; результат применяется под select_for_update
  в порядке «заказ → платёж → возврат» (без взаимных блокировок);
- повторная сверка того же статуса ничего не меняет (повторный webhook, параллельная сверка);
- деньги, которые не могут оплатить заказ (заказ уже отменён или оплачен, сумма не совпала),
  возвращаются автоматически;
- возврат — только полный; выполняется фоновой задачей после commit, сбой сети — повтор
  периодической сверкой.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from content import shop as shop_settings
from core.tasks import send_email
from orders.models import ChangedBy, Order, OrderStatus, PaymentMethod
from orders.services import status as status_service

from . import providers
from .models import Payment, PaymentStatus, Refund, RefundReason, RefundStatus
from .providers import ProviderError, RemotePayment, RemoteRefund
from .receipts import build_receipt

logger = logging.getLogger(__name__)

# Провайдер ещё не ответил на создание: через столько платёж считается несозданным.
ABANDONED_CREATE_AFTER = timedelta(minutes=10)
# Свежие платежи и возвраты периодическая сверка не трогает: их обновит webhook или клиент.
SYNC_GRACE = timedelta(minutes=1)
SYNC_BATCH = 200


class PaymentUnavailable(Exception):
    """Провайдер временно недоступен: повторить позже (API отвечает 503)."""


def _new_key() -> str:
    return uuid.uuid4().hex


# --- Сведения для клиентов ---


def pay_until(order: Order) -> datetime | None:
    """Срок оплаты онлайн-заказа; после него заказ отменяется автоматически."""
    if order.payment_method != PaymentMethod.ONLINE or order.status != OrderStatus.AWAITING_PAYMENT:
        return None
    return order.created_at + timedelta(minutes=shop_settings.current().unpaid_timeout_minutes)


def can_pay(order: Order) -> bool:
    deadline = pay_until(order)
    return deadline is not None and timezone.now() < deadline


@dataclass(frozen=True)
class PaymentSummary:
    can_pay: bool
    pay_until: datetime | None
    payment_status: str | None
    refund_status: str | None


def summary(order: Order) -> PaymentSummary:
    """Состояние оплаты для экрана заказа. Использует order.payments.all() (prefetch)."""
    payments = list(order.payments.all())
    last_payment = payments[-1] if payments else None
    refunds = [refund for payment in payments for refund in payment.refunds.all()]
    last_refund = max(refunds, key=lambda r: (r.created_at, r.pk)) if refunds else None
    return PaymentSummary(
        can_pay=can_pay(order),
        pay_until=pay_until(order),
        payment_status=last_payment.status if last_payment else None,
        refund_status=last_refund.status if last_refund else None,
    )


def refund_retry_payment(order: Order) -> Payment | None:
    """Платёж, по которому администратор может повторить возврат: деньги списаны, а активного
    возврата нет — прошлый отклонён провайдером, или заказ отменён без возврата."""
    for payment in order.payments.all():
        if payment.status != PaymentStatus.SUCCEEDED:
            continue
        refunds = list(payment.refunds.all())
        if any(r.status != RefundStatus.CANCELED for r in refunds):
            continue
        if refunds or order.status == OrderStatus.CANCELLED:
            return payment
    return None


# --- Создание платежа ---


def validate_return_url(url: str, order: Order) -> str:
    """Куда провайдер вернёт покупателя. Только адреса приложения из
    PAYMENTS_RETURN_URL_PREFIXES — страница оплаты не станет открытым редиректом."""
    url = (url or "").strip()
    if not url:
        return settings.PAYMENTS_DEFAULT_RETURN_URL.format(number=order.number)
    prefixes = tuple(settings.PAYMENTS_RETURN_URL_PREFIXES)
    if len(url) > 1000 or any(ch.isspace() for ch in url) or not url.startswith(prefixes):
        raise ValidationError({"return_url": ["Недопустимый адрес возврата в приложение."]})
    return url


def _not_payable_message(order: Order) -> str:
    if order.payment_method != PaymentMethod.ONLINE:
        return "Этот заказ оплачивается при получении."
    if order.status == OrderStatus.AWAITING_PAYMENT:
        return "Время на оплату истекло — заказ будет отменён. Оформите заказ заново."
    if order.status == OrderStatus.CANCELLED:
        return "Заказ отменён, оплатить его нельзя."
    return "Заказ уже оплачен."


def start_payment(order: Order, *, return_url: str = "") -> Payment:
    """Ссылка на страницу оплаты. Повторный вызов возвращает ту же попытку, пока она не
    завершилась (одна pending-попытка на заказ, повтор запроса к провайдеру — с тем же ключом)."""
    return_url = validate_return_url(return_url, order)
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if not can_pay(locked):
            raise ValidationError(_not_payable_message(locked), code="not_payable")
        payment = locked.payments.filter(status=PaymentStatus.PENDING).first()
        if payment is None:
            payment = Payment.objects.create(
                order=locked, amount_kopecks=locked.total_kopecks, idempotency_key=_new_key()
            )
        if payment.confirmation_url:
            return payment

    try:
        provider = providers.get_provider()
        remote = provider.create_payment(
            amount_kopecks=payment.amount_kopecks,
            description=f"Заказ {order.number} в DiDi-shop",
            return_url=return_url,
            idempotency_key=payment.idempotency_key,
            metadata={"order_number": order.number, "payment_id": str(payment.pk)},
            receipt=build_receipt(order),
        )
    except ProviderError as exc:
        if exc.transient:
            logger.warning("Платёж %s не создан, повторим: %s", payment.pk, exc)
            raise PaymentUnavailable(str(exc)) from exc
        logger.error("Провайдер отклонил платёж %s: %s", payment.pk, exc)
        Payment.objects.filter(pk=payment.pk, status=PaymentStatus.PENDING).update(
            status=PaymentStatus.CANCELED, cancellation_reason="rejected_by_provider"
        )
        raise ValidationError(
            "Не удалось создать платёж. Попробуйте позже или выберите оплату при получении.",
            code="payment_rejected",
        ) from exc
    return _apply_payment(payment.pk, remote)


# --- Сверка платежа ---


def sync_payment(payment: Payment) -> Payment:
    """Запросить статус у провайдера и применить. ProviderError пробрасывается."""
    if not payment.provider_payment_id:
        return payment
    remote = providers.get_provider().get_payment(payment.provider_payment_id)
    return _apply_payment(payment.pk, remote)


def sync_order_payments(order: Order) -> None:
    """Сверка незавершённых платежей заказа (возврат из приложения, автоотмена).
    Временная недоступность провайдера не ошибка: статус обновит webhook или следующая сверка."""
    pending = order.payments.filter(status=PaymentStatus.PENDING).exclude(provider_payment_id=None)
    for payment in pending:
        try:
            sync_payment(payment)
        except ProviderError as exc:
            logger.warning("Сверка платежа %s не удалась: %s", payment.pk, exc)
            if exc.transient:
                raise PaymentUnavailable(str(exc)) from exc


@transaction.atomic
def _apply_payment(payment_pk: int, remote: RemotePayment) -> Payment:
    order_id = Payment.objects.values_list("order_id", flat=True).get(pk=payment_pk)
    order = Order.objects.select_for_update().get(pk=order_id)
    payment = Payment.objects.select_for_update().get(pk=payment_pk)

    if payment.provider_payment_id and payment.provider_payment_id != remote.id:
        logger.error(
            "Платёж %s: провайдер вернул чужой id %s (ожидали %s)",
            payment.pk,
            remote.id,
            payment.provider_payment_id,
        )
        return payment

    payment.provider_payment_id = remote.id
    payment.payload = remote.raw
    if remote.confirmation_url:
        payment.confirmation_url = remote.confirmation_url
    fields = ["provider_payment_id", "payload", "confirmation_url", "updated_at"]

    # Итог уже применён (повторный webhook, параллельная сверка): статус не меняется.
    if payment.status != PaymentStatus.PENDING:
        payment.save(update_fields=fields)
        return payment

    if remote.status == "succeeded":
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save(update_fields=[*fields, "status", "paid_at"])
        _on_succeeded(payment, order, remote)
    elif remote.status == "canceled":
        payment.status = PaymentStatus.CANCELED
        payment.cancellation_reason = remote.cancellation_reason[:100]
        payment.save(update_fields=[*fields, "status", "cancellation_reason"])
    else:
        if remote.status == "waiting_for_capture":
            # Одностадийная оплата (capture=true) сюда не приходит; ждём решения провайдера.
            logger.error("Платёж %s ждёт подтверждения, хотя capture=true", payment.pk)
        payment.save(update_fields=fields)
    return payment


def _on_succeeded(payment: Payment, order: Order, remote: RemotePayment) -> None:
    amount_ok = (
        remote.currency == "RUB"
        and remote.amount_kopecks == payment.amount_kopecks == order.total_kopecks
    )
    if not amount_ok:
        logger.error(
            "Платёж %s заказа %s: списано %s %s, ожидали %s RUB — возврат",
            payment.pk,
            order.number,
            remote.amount_kopecks,
            remote.currency,
            order.total_kopecks,
        )
        _create_refund(payment, RefundReason.AMOUNT_MISMATCH, remote.amount_kopecks)
        return
    if order.status == OrderStatus.AWAITING_PAYMENT:
        status_service.mark_paid(order)
        return
    if order.status == OrderStatus.CANCELLED:
        logger.warning("Заказ %s оплачен после отмены — возврат", order.number)
        _create_refund(payment, RefundReason.LATE_PAYMENT)
        return
    logger.warning("Заказ %s оплачен повторно — возврат платежа %s", order.number, payment.pk)
    _create_refund(payment, RefundReason.DUPLICATE_PAYMENT)


# --- Возвраты ---


def _create_refund(payment: Payment, reason: str, amount_kopecks: int | None = None) -> Refund:
    """Вызывать внутри транзакции: задача стартует только после commit."""
    from .tasks import execute_refund

    refund = Refund.objects.create(
        payment=payment,
        amount_kopecks=amount_kopecks or payment.amount_kopecks,
        reason=reason,
        idempotency_key=_new_key(),
    )
    transaction.on_commit(lambda: execute_refund.enqueue(refund.pk))
    return refund


def refund_cancelled_order(order: Order) -> Refund | None:
    """Оплаченный заказ отменён (сигнал order_cancelled, внутри транзакции отмены)."""
    payment = (
        Payment.objects.select_for_update()
        .filter(order=order, status=PaymentStatus.SUCCEEDED)
        .order_by("created_at", "pk")
        .first()
    )
    if payment is None:
        logger.error("Заказ %s отменён как оплаченный, но платежа нет", order.number)
        return None
    if payment.refunds.exclude(status=RefundStatus.CANCELED).exists():
        return None
    return _create_refund(payment, RefundReason.ORDER_CANCELLED)


def retry_refund(order: Order) -> Refund:
    """Повторный возврат из панели после отказа провайдера."""
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        payment = refund_retry_payment(locked)
        if payment is None:
            raise ValidationError("По заказу нет платежа, ожидающего возврата.", code="no_refund")
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        last = payment.refunds.order_by("-created_at", "-pk").first()
        reason = last.reason if last else RefundReason.ORDER_CANCELLED
        amount = last.amount_kopecks if last else payment.amount_kopecks
        return _create_refund(payment, reason, amount)


def execute_refund(refund_pk: int) -> Refund:
    """Отправить возврат провайдеру (или узнать его статус). Ключ идемпотентности постоянный:
    повтор после сбоя сети не создаст второй возврат."""
    refund = Refund.objects.select_related("payment__order__owner").get(pk=refund_pk)
    if refund.status != RefundStatus.PENDING:
        return refund
    payment = refund.payment
    order = payment.order
    try:
        provider = providers.get_provider()
        if refund.provider_refund_id:
            remote = provider.get_refund(refund.provider_refund_id)
        else:
            full = refund.amount_kopecks == order.total_kopecks
            remote = provider.create_refund(
                payment_id=payment.provider_payment_id,
                amount_kopecks=refund.amount_kopecks,
                idempotency_key=refund.idempotency_key,
                description=f"Возврат по заказу {order.number}",
                # Чек возврата — на те же позиции; при несовпавшей сумме позиции не сходятся.
                receipt=build_receipt(order) if full else None,
            )
    except ProviderError as exc:
        if exc.transient:
            logger.warning("Возврат %s отложен: %s", refund.pk, exc)
            return refund
        logger.error("Провайдер отклонил возврат %s: %s", refund.pk, exc)
        Refund.objects.filter(pk=refund.pk, status=RefundStatus.PENDING).update(
            status=RefundStatus.CANCELED, cancellation_reason="rejected_by_provider"
        )
        refund.refresh_from_db()
        return refund
    return _apply_refund(refund.pk, remote)


def sync_refund(refund: Refund) -> Refund:
    if refund.status != RefundStatus.PENDING or not refund.provider_refund_id:
        return refund
    remote = providers.get_provider().get_refund(refund.provider_refund_id)
    return _apply_refund(refund.pk, remote)


@transaction.atomic
def _apply_refund(refund_pk: int, remote: RemoteRefund) -> Refund:
    payment_id = Refund.objects.values_list("payment_id", flat=True).get(pk=refund_pk)
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    refund = Refund.objects.select_for_update().get(pk=refund_pk)

    refund.provider_refund_id = remote.id
    refund.payload = remote.raw
    fields = ["provider_refund_id", "payload", "updated_at"]
    if refund.status != RefundStatus.PENDING:
        refund.save(update_fields=fields)
        return refund

    if remote.status == "succeeded":
        refund.status = RefundStatus.SUCCEEDED
        refund.save(update_fields=[*fields, "status"])
        payment.status = PaymentStatus.REFUNDED
        payment.save(update_fields=["status", "updated_at"])
        _notify_refunded(refund, payment)
    elif remote.status == "canceled":
        refund.status = RefundStatus.CANCELED
        refund.cancellation_reason = remote.cancellation_reason[:100]
        refund.save(update_fields=[*fields, "status", "cancellation_reason"])
        logger.error("Провайдер отклонил возврат %s: %s", refund.pk, remote.cancellation_reason)
    else:
        refund.save(update_fields=fields)
    return refund


def _notify_refunded(refund: Refund, payment: Payment) -> None:
    order = Order.objects.select_related("owner").get(pk=payment.order_id)
    owner = order.owner
    if owner.deleted_at is not None or not owner.email:
        return
    subject = f"DiDi-shop: деньги за заказ {order.number} возвращены"
    body = render_to_string(
        "payments/email/refund_succeeded.txt",
        {"order": order, "refund": refund, "first_name": owner.first_name},
    )
    recipient = owner.email
    transaction.on_commit(lambda: send_email.enqueue(subject, body, [recipient]))


# --- Webhook ---


def handle_notification(data: dict) -> None:
    """Уведомление провайдера — только повод перезапросить объект по API.
    Неизвестные объекты и события игнорируются; временная ошибка API — ProviderError
    (webhook отвечает 5xx, провайдер повторит уведомление)."""
    event = str(data.get("event", ""))
    obj = data.get("object")
    object_id = obj.get("id") if isinstance(obj, dict) else None
    if not isinstance(object_id, str) or not object_id:
        raise ValidationError("Некорректное уведомление.")

    if event.startswith("payment."):
        payment = Payment.objects.filter(provider_payment_id=object_id).first()
        if payment is None:
            logger.warning("Webhook %s: платёж %s не найден", event, object_id)
            return
        sync_payment(payment)
    elif event.startswith("refund."):
        refund = Refund.objects.filter(provider_refund_id=object_id).first()
        if refund is None:
            logger.warning("Webhook %s: возврат %s не найден", event, object_id)
            return
        sync_refund(refund)
    else:
        logger.info("Webhook: событие %s пропущено", event)


# --- Периодические задачи ---


def sync_stale() -> None:
    """Зависшие платежи и возвраты: webhook потерян или провайдер был недоступен."""
    now = timezone.now()
    Payment.objects.filter(
        status=PaymentStatus.PENDING,
        provider_payment_id=None,
        created_at__lt=now - ABANDONED_CREATE_AFTER,
    ).update(status=PaymentStatus.CANCELED, cancellation_reason="not_created")

    payments = Payment.objects.filter(
        status=PaymentStatus.PENDING, created_at__lt=now - SYNC_GRACE
    ).exclude(provider_payment_id=None)
    for payment in payments.order_by("created_at")[:SYNC_BATCH]:
        try:
            sync_payment(payment)
        except ProviderError as exc:
            logger.warning("Сверка платежа %s не удалась: %s", payment.pk, exc)

    refunds = Refund.objects.filter(status=RefundStatus.PENDING, created_at__lt=now - SYNC_GRACE)
    for refund_pk in refunds.order_by("created_at").values_list("pk", flat=True)[:SYNC_BATCH]:
        execute_refund(refund_pk)


def cancel_if_unpaid(order: Order) -> bool:
    """Автоотмена просроченного онлайн-заказа. Сначала сверка: оплаченный заказ не отменяем.
    Если провайдер недоступен — не отменяем, повторим на следующем запуске."""
    try:
        sync_order_payments(order)
    except PaymentUnavailable:
        return False
    if not cancel_awaiting_payment(order):
        return False
    logger.info("Заказ %s не оплачен вовремя и отменён", order.number)
    return True


@transaction.atomic
def cancel_awaiting_payment(order: Order) -> bool:
    """Отменить заказ, только если он всё ещё ждёт оплаты: оплата, подтверждённая параллельно,
    уже перевела его в «Оплачен» под той же блокировкой."""
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status != OrderStatus.AWAITING_PAYMENT:
        return False
    status_service.cancel(locked, by=ChangedBy.SYSTEM)
    return True


def cancel_unpaid_orders() -> int:
    deadline = timezone.now() - timedelta(minutes=shop_settings.current().unpaid_timeout_minutes)
    orders = Order.objects.filter(
        status=OrderStatus.AWAITING_PAYMENT, created_at__lt=deadline
    ).order_by("created_at")[:SYNC_BATCH]
    return sum(1 for order in orders if cancel_if_unpaid(order))
