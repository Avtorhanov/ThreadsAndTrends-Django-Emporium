"""Чек 54-ФЗ для ЮKassa («Чеки от ЮKassa»): позиции из снимка заказа + доставка.

Система налогообложения, ставка НДС и признак способа расчёта — настройки
(PAYMENTS_TAX_SYSTEM_CODE, PAYMENTS_VAT_CODE, PAYMENTS_RECEIPT_PAYMENT_MODE): их выбирает
владелец вместе с бухгалтером, код не меняется. PAYMENTS_RECEIPTS_ENABLED=False — без чеков
(например, самозанятый выдаёт чек через «Мой налог»).
"""

from django.conf import settings

from orders.models import Order

from .providers.yookassa import DESCRIPTION_MAX, money


def _line(description: str, quantity: int, price_kopecks: int, subject: str) -> dict:
    return {
        "description": description[:DESCRIPTION_MAX],
        "quantity": quantity,
        "amount": money(price_kopecks),  # цена за единицу
        "vat_code": settings.PAYMENTS_VAT_CODE,
        "payment_mode": settings.PAYMENTS_RECEIPT_PAYMENT_MODE,
        "payment_subject": subject,
    }


def build_receipt(order: Order) -> dict | None:
    """Чек на всю сумму заказа (оплата и полный возврат). Сумма позиций = Order.total_kopecks."""
    if not settings.PAYMENTS_RECEIPTS_ENABLED:
        return None
    items = []
    for item in order.items.all():
        name = f"{item.product_name}, размер {item.size}" if item.size else item.product_name
        items.append(_line(name, item.quantity, item.price_kopecks, "commodity"))
    if order.delivery_kopecks:
        items.append(_line("Доставка", 1, order.delivery_kopecks, "service"))
    return {
        "customer": {"email": order.owner.email},
        "items": items,
        "tax_system_code": settings.PAYMENTS_TAX_SYSTEM_CODE,
    }
