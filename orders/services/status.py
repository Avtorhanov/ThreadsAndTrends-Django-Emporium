"""Жизненный цикл заказа (state machine).

Онлайн-оплата:    awaiting_payment → paid → assembled → …
При получении:    confirmed → assembled → …
Далее:            assembled → shipped (курьер) | ready_for_pickup (самовывоз) → delivered
Отмена:           из любого незавершённого статуса, кроме shipped.

Кто что может:
- клиент — только отменить свой заказ до отправки (awaiting_payment, confirmed, paid, assembled);
- администратор — сборка, отправка, выдача, отмена; «Оплачен» вручную не ставит;
- система — «Оплачен» по подтверждению провайдера (mark_paid, сессия 6).

Отмена возвращает остатки и отправляет сигнал order_cancelled (возврат денег — сессия 6).
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from orders.models import (
    ChangedBy,
    DeliveryMethod,
    Order,
    OrderStatus,
    OrderStatusChange,
    PaymentMethod,
)
from orders.signals import order_cancelled
from store.models import ProductVariant

from . import notifications

S = OrderStatus

TRANSITIONS: dict[str, frozenset[str]] = {
    S.AWAITING_PAYMENT: frozenset({S.PAID, S.CANCELLED}),
    S.CONFIRMED: frozenset({S.ASSEMBLED, S.CANCELLED}),
    S.PAID: frozenset({S.ASSEMBLED, S.CANCELLED}),
    S.ASSEMBLED: frozenset({S.SHIPPED, S.READY_FOR_PICKUP, S.CANCELLED}),
    S.SHIPPED: frozenset({S.DELIVERED}),
    S.READY_FOR_PICKUP: frozenset({S.DELIVERED, S.CANCELLED}),
}

# Статус доступен только при этом способе доставки.
REQUIRED_DELIVERY = {
    S.SHIPPED: DeliveryMethod.COURIER,
    S.READY_FOR_PICKUP: DeliveryMethod.PICKUP,
}

SYSTEM_ONLY = frozenset({S.PAID})
CUSTOMER_CANCELLABLE = frozenset({S.AWAITING_PAYMENT, S.CONFIRMED, S.PAID, S.ASSEMBLED})


def initial_status(payment_method: str) -> str:
    return S.AWAITING_PAYMENT if payment_method == PaymentMethod.ONLINE else S.CONFIRMED


def allowed_transitions(order: Order, by: str) -> list[str]:
    """Статусы, в которые `by` может перевести заказ сейчас (в порядке OrderStatus)."""
    targets = TRANSITIONS.get(order.status, frozenset())
    result = []
    for target in S.values:
        if target not in targets:
            continue
        required = REQUIRED_DELIVERY.get(target)
        if required and order.delivery_method != required:
            continue
        if by == ChangedBy.ADMIN and target in SYSTEM_ONLY:
            continue
        if by == ChangedBy.CUSTOMER and not (
            target == S.CANCELLED and order.status in CUSTOMER_CANCELLABLE
        ):
            continue
        result.append(target)
    return result


def can_cancel(order: Order, by: str) -> bool:
    return S.CANCELLED in allowed_transitions(order, by)


@transaction.atomic
def transition(order: Order, to_status: str, *, by: str, actor=None) -> Order:
    """Перевести заказ в статус. Повтор того же статуса — без изменений (повторный клик,
    повторный webhook). Недопустимый переход — ValidationError."""
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status == to_status:
        return locked
    if to_status not in allowed_transitions(locked, by):
        raise ValidationError(
            f"Нельзя перевести заказ из статуса «{S(locked.status).label}» "
            f"в «{S(to_status).label if to_status in S.values else to_status}».",
            code="invalid_transition",
        )

    from_status = locked.status
    locked.status = to_status
    locked.save(update_fields=["status", "updated_at"])
    OrderStatusChange.objects.create(
        order=locked,
        from_status=from_status,
        to_status=to_status,
        changed_by=by,
        actor=actor,
    )
    if to_status == S.CANCELLED:
        _return_stock(locked)
        order_cancelled.send(sender=Order, order=locked, was_paid=_was_paid(locked))
    notifications.notify_status(locked)
    return locked


def cancel(order: Order, *, by: str, actor=None) -> Order:
    return transition(order, S.CANCELLED, by=by, actor=actor)


def mark_paid(order: Order) -> Order:
    """Оплата подтверждена провайдером (вызывают платежи, сессия 6)."""
    return transition(order, S.PAID, by=ChangedBy.SYSTEM)


def _was_paid(order: Order) -> bool:
    return (
        order.payment_method == PaymentMethod.ONLINE
        and order.status_changes.filter(to_status=S.PAID).exists()
    )


def _return_stock(order: Order) -> None:
    # Порядок по variant_id — тот же, что при блокировке в checkout: без взаимных блокировок.
    for variant_id, quantity in order.items.order_by("variant_id").values_list(
        "variant_id", "quantity"
    ):
        ProductVariant.all_objects.filter(pk=variant_id).update(stock=F("stock") + quantity)
