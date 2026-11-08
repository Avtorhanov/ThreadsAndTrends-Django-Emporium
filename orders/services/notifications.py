"""Письма об оформлении и смене статуса заказа (фоновая задача core.tasks.send_email):
покупателю — о каждом шаге, продавцу (email из реквизитов) — о новом заказе."""

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from content import shop as shop_settings
from core.tasks import send_email
from orders.models import Order, OrderStatus, PaymentMethod


def can_notify(order: Order) -> bool:
    owner = order.owner
    return owner.deleted_at is None and bool(owner.email)


def subject_for(order: Order, status: str, *, created: bool = False) -> str:
    if created and order.payment_method == PaymentMethod.AGREEMENT:
        return f"DiDi-shop: заказ {order.number} — напишите продавцу"
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
            "agreement": order.payment_method == PaymentMethod.AGREEMENT,
            "agreement_hours": shop_settings.current().agreement_timeout_hours,
        },
    )
    recipient = owner.email
    transaction.on_commit(lambda: send_email.enqueue(subject, body, [recipient]))
    return True


def notify_seller(order: Order, *, cancelled: bool = False) -> bool:
    """Письмо продавцу о новом заказе (по согласованию и при получении — сразу, онлайн — после
    оплаты) или об отмене заказа покупателем. Адрес — email из реквизитов продавца; не задан —
    письма нет."""
    recipient = shop_settings.current().seller.email
    if not recipient:
        return False
    panel_url = f"{settings.SITE_URL}/panel/orders/{order.pk}" if settings.SITE_URL else ""
    subject = (
        f"Покупатель отменил заказ {order.number}"
        if cancelled
        else f"Новый заказ {order.number} — {OrderStatus(order.status).label.lower()}"
    )
    body = render_to_string(
        "orders/email/new_order_seller.txt",
        {
            "order": order,
            "items": list(order.items.all()),
            "status_label": OrderStatus(order.status).label,
            "panel_url": panel_url,
            "cancelled": cancelled,
        },
    )
    transaction.on_commit(lambda: send_email.enqueue(subject, body, [recipient]))
    return True
