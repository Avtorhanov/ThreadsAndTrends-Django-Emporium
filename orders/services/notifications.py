"""Письма клиенту об оформлении и смене статуса заказа (фоновая задача core.tasks.send_email)."""

from django.db import transaction
from django.template.loader import render_to_string

from core.tasks import send_email
from orders.models import Order, OrderStatus


def notify_status(order: Order, *, created: bool = False) -> None:
    """Письмо уходит только после commit: откат транзакции письмо не отправляет."""
    owner = order.owner
    if owner.deleted_at is not None or not owner.email:
        return
    status_label = OrderStatus(order.status).label
    subject = (
        f"DiDi-shop: заказ {order.number} оформлен"
        if created
        else f"DiDi-shop: заказ {order.number} — {status_label.lower()}"
    )
    body = render_to_string(
        "orders/email/status_changed.txt",
        {
            "order": order,
            "items": list(order.items.all()) if created else [],
            "created": created,
            "status_label": status_label,
            "first_name": owner.first_name,
        },
    )
    recipient = owner.email
    transaction.on_commit(lambda: send_email.enqueue(subject, body, [recipient]))
