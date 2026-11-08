"""Оформление «по согласованию с продавцом»: канал заказа, сообщение продавцу, автоотмена.

Покупатель оформляет заказ (остатки резервируются, статус «Ждёт согласования») и пишет продавцу
в мессенджер готовым текстом: номер заказа, товары со ссылками, сумма. Продавец находит заказ
по номеру в панели и переводит в «Принят» (дальше — обычный путь заказа) или отменяет.
Не подтверждённый за agreement_timeout_hours заказ отменяется, товар возвращается в продажу.

Канал: если у всех товаров заказа один и тот же канал (свой у товара или канал магазина) — он,
иначе канал магазина. Ссылка — из контактов магазина; выбранный канал не задан — первый заданный
по порядку contacts.AGREEMENT_KINDS. WhatsApp подставляет текст в чат (?text=); Telegram
и ВКонтакте открывают чат без текста — покупатель вставляет скопированный текст; телефон — звонок.
"""

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from urllib.parse import quote

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from content import contacts
from content import shop as shop_settings
from core.choices import AgreementChannel
from orders.models import ChangedBy, Order, OrderStatus, PaymentMethod
from store.templatetags.money import NBSP, format_kopecks

from . import status as status_service

logger = logging.getLogger(__name__)
STALE_BATCH = 100


@dataclass(frozen=True)
class AgreementLink:
    kind: str
    title: str  # «WhatsApp» или своя подпись контакта
    url: str  # https://wa.me/…?text=…, https://t.me/…, https://vk.com/…, tel:+7…
    handle: str  # «+7 900 123-45-67», «@didishop»
    message: str  # текст для продавца (WhatsApp — уже в ссылке, остальным — скопировать)
    prefilled: bool  # текст подставляется в чат сам
    deadline: datetime  # после этого заказ отменится, если продавец не подтвердит


def choose_channel(products) -> str:
    """Канал заказа из каналов его товаров (пустой у товара — канал магазина)."""
    default = shop_settings.current().agreement_channel
    channels = {product.agreement_channel or default for product in products}
    return channels.pop() if len(channels) == 1 else default


def _rub(kopecks: int) -> str:
    return format_kopecks(kopecks).replace(NBSP, " ") + " ₽"


def message(order: Order, base_url: str) -> str:
    """Текст продавцу: номер заказа, позиции со ссылками на товары, доставка и сумма."""
    lines = [f"Здравствуйте! Хочу оформить заказ {order.number}.", ""]
    for n, item in enumerate(order.items.all(), start=1):
        color = f", {item.color_name}" if item.color_name else ""
        size = f", {item.size}" if item.size else ""
        lines.append(
            f"{n}. {item.product_name}{color}{size} × {item.quantity} — "
            f"{_rub(item.price_kopecks * item.quantity)}"
        )
        lines.append(base_url + reverse("web:product", kwargs={"slug": item.product.slug}))
    delivery = order.get_delivery_method_display()
    cost = _rub(order.delivery_kopecks) if order.delivery_kopecks else "бесплатно"
    lines += ["", f"Доставка: {delivery.lower()}, {cost}", f"Итого: {_rub(order.total_kopecks)}"]
    return "\n".join(lines)


def deadline(order: Order) -> datetime:
    return order.created_at + timedelta(hours=shop_settings.current().agreement_timeout_hours)


def _contact(kind: str) -> contacts.Contact | None:
    available = {c.kind: c for c in contacts.agreement_contacts() if c.url}
    if kind in available:
        return available[kind]
    return next((available[k] for k in contacts.AGREEMENT_KINDS if k in available), None)


def link(order: Order, base_url: str) -> AgreementLink | None:
    """Кнопка связи с продавцом — пока заказ ждёт согласования. None — не ждёт или у магазина
    не задан ни один канал (покупателю остаётся ждать звонка по телефону из заказа)."""
    if order.status != OrderStatus.AWAITING_AGREEMENT:
        return None
    contact = _contact(order.agreement_channel or shop_settings.current().agreement_channel)
    if contact is None:
        return None
    text = message(order, base_url)
    prefilled = contact.kind == AgreementChannel.WHATSAPP
    if prefilled:
        contact = replace(contact, url=f"{contact.url}?text={quote(text)}")
    return AgreementLink(
        kind=contact.kind,
        title=contact.title,
        url=contact.url,
        handle=contact.handle,
        message=text,
        prefilled=prefilled,
        deadline=deadline(order),
    )


@transaction.atomic
def _cancel_if_stale(order: Order, hours: int) -> bool:
    # Продавец мог подтвердить заказ параллельно: проверка статуса — под блокировкой строки.
    locked = Order.objects.select_for_update().get(pk=order.pk)
    if locked.status != OrderStatus.AWAITING_AGREEMENT:
        return False
    status_service.transition(
        locked,
        OrderStatus.CANCELLED,
        by=ChangedBy.SYSTEM,
        comment=f"Продавец не подтвердил заказ за {hours} ч — заказ отменён, "
        "товар вернулся в продажу.",
    )
    return True


def cancel_stale() -> int:
    """Отменить заказы «по согласованию», не подтверждённые за agreement_timeout_hours."""
    hours = shop_settings.current().agreement_timeout_hours
    limit = timezone.now() - timedelta(hours=hours)
    orders = Order.objects.filter(
        status=OrderStatus.AWAITING_AGREEMENT,
        payment_method=PaymentMethod.AGREEMENT,
        created_at__lt=limit,
    ).order_by("created_at")[:STALE_BATCH]
    cancelled = 0
    for order in orders:
        if _cancel_if_stale(order, hours):
            logger.info("Заказ %s не согласован за %s ч и отменён", order.number, hours)
            cancelled += 1
    return cancelled
