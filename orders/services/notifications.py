"""Письма клиенту об оформлении и смене статуса заказа (фоновая задача core.tasks.send_email)."""

from django.db import transaction
from django.template.loader import render_to_string

from core.tasks import send_email
from orders.models import Order, OrderStatus


def can_notify(order: Order) -> bool:
    owner = order.owner
    return owner.deleted_at is None and bool(owner.email)


def subject_for(order: Order, status: str, *, created: bool = False) -> str:
    if created:
        return f"DiDi-shop: заказ {order.number} оформлен"
    return f"DiDi-shop: заказ {order.number} — {OrderStatus(status).label.lower()}"


def notify_status(order: Order, *, created: bool = False, comment: str = "") -> bool:
    """Письмо уходит только после commit: откат транзакции письмо не отправляет.
    Возвращает, поставлено ли письмо в очередь (нет адреса или аккаунт удалён — нет)."""
    if not can_notify(order):
        return False
    owner = order.owner
    status_label = OrderStatus(order.status).label
    subject = subject_for(order, order.status, created=created)
    body = render_to_string(
        "orders/email/status_changed.txt",
        {
            "order": order,
            "items": list(order.items.all()) if created else [],
            "created": created,
            "status_label": status_label,
            "first_name": owner.first_name,
            "comment": comment,
        },
    )
    recipient = owner.email
    transaction.on_commit(lambda: send_email.enqueue(subject, body, [recipient]))
    return True
