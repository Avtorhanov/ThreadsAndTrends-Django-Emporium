"""Общие справочники, которые нужны моделям разных приложений (без импорта между ними)."""

from django.db import models


class AgreementChannel(models.TextChoices):
    """Канал, в котором покупатель согласует заказ с продавцом (оплата «по согласованию»).
    Значения совпадают с content.contacts.ContactKind: ссылка берётся из контактов магазина."""

    WHATSAPP = "whatsapp", "WhatsApp"
    TELEGRAM = "telegram", "Telegram"
    VK = "vk", "ВКонтакте"
    PHONE = "phone", "Телефон"
