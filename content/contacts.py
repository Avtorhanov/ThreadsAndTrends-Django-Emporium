"""Контакты магазина для вкладки «Контакты» (сайт и приложение).

Значения — из настроек (.env), одна строка на канал: WhatsApp — номер телефона, Telegram —
имя (@shop) или ссылка t.me, ВКонтакте — короткое имя или ссылка vk.com. Подписи — свои
у каждого канала. Пустое или неверное значение — канал не показывается (неверное видно
в `manage.py check`, content.W001). Телефон и email — реквизиты продавца (SELLER_*).
"""

import re
from dataclasses import dataclass, replace
from urllib.parse import quote

from django.conf import settings


class ContactKind:
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    VK = "vk"
    PHONE = "phone"
    EMAIL = "email"
    CHOICES = [
        (WHATSAPP, "WhatsApp"),
        (TELEGRAM, "Telegram"),
        (VK, "ВКонтакте"),
        (PHONE, "Телефон"),
        (EMAIL, "Почта"),
    ]


@dataclass(frozen=True)
class Contact:
    kind: str
    title: str
    url: str
    handle: str  # как показать: «+7 900 123-45-67», «@didishop», «vk.com/didishop»
    note: str
    # Номер блока в разделе «Контакты» (content.site.blocks) — для правки с сайта.
    index: int = -1


_TG_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
_VK_NAME = re.compile(r"^[A-Za-z0-9_.]{2,64}$")


def _phone_digits(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    return digits if 11 <= len(digits) <= 15 else None


def _format_phone(digits: str) -> str:
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    return f"+{digits}"


def whatsapp(value: str) -> tuple[str, str] | None:
    digits = _phone_digits(value)
    if digits is None:
        return None
    return f"https://wa.me/{digits}", _format_phone(digits)


def telegram(value: str) -> tuple[str, str] | None:
    name = re.sub(r"^(https?://)?(t\.me|telegram\.me)/", "", value.strip()).lstrip("@").strip("/")
    if not _TG_NAME.match(name):
        return None
    return f"https://t.me/{name}", f"@{name}"


def vk(value: str) -> tuple[str, str] | None:
    name = re.sub(r"^(https?://)?(m\.)?vk\.(com|ru)/", "", value.strip()).strip("/")
    if not _VK_NAME.match(name):
        return None
    return f"https://vk.com/{name}", f"vk.com/{name}"


def phone(value: str) -> tuple[str, str] | None:
    digits = _phone_digits(value)
    if digits is None:
        return None
    return f"tel:+{digits}", _format_phone(digits)


def email(value: str) -> tuple[str, str] | None:
    value = value.strip()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return None
    return f"mailto:{value}", value


# Канал → (настройка со значением, настройка с подписью, разбор, подпись по умолчанию)
CHANNELS = [
    (
        ContactKind.WHATSAPP,
        "CONTACT_WHATSAPP",
        "CONTACT_WHATSAPP_NOTE",
        whatsapp,
        "Ответим на вопросы о заказе и размерах",
    ),
    (
        ContactKind.TELEGRAM,
        "CONTACT_TELEGRAM",
        "CONTACT_TELEGRAM_NOTE",
        telegram,
        "Новинки, скидки и быстрые ответы",
    ),
    (ContactKind.VK, "CONTACT_VK", "CONTACT_VK_NOTE", vk, "Сообщество магазина"),
    (ContactKind.PHONE, "SELLER_PHONE", "CONTACT_PHONE_NOTE", phone, "Позвонить в магазин"),
    (ContactKind.EMAIL, "SELLER_EMAIL", "CONTACT_EMAIL_NOTE", email, "Для писем и документов"),
]
TITLES = dict(ContactKind.CHOICES)


PARSERS = {kind: parse for kind, _, _, parse, _ in CHANNELS}
DEFAULT_NOTES = {kind: note for kind, _, _, _, note in CHANNELS}


def default_values() -> list[tuple[str, str, str]]:
    """Каналы из настроек (.env): (канал, значение, своя подпись или пусто)."""
    rows = []
    for kind, value_setting, note_setting, _, _ in CHANNELS:
        value = (getattr(settings, value_setting, "") or "").strip()
        if value:
            rows.append((kind, value, getattr(settings, note_setting, "") or ""))
    return rows


def get_contacts() -> list[Contact]:
    """Каналы связи. Пока администратор не менял раздел на сайте — из настроек (.env),
    потом — из блоков раздела «Контакты». Неразобранные значения не показываются."""
    from content import site

    contacts = []
    for index, block in enumerate(site.blocks("contacts")):
        parse = PARSERS.get(block.kind)
        parsed = parse(block.value) if parse else None
        if parsed is None:
            continue
        url, handle = parsed
        title = block.title or TITLES[block.kind]
        note = block.note or DEFAULT_NOTES[block.kind]
        contacts.append(Contact(block.kind, title, url, handle, note, index))
    return contacts


def invalid_settings() -> list[str]:
    """Заданные, но неразобранные значения — для system check."""
    return [
        value_setting
        for _, value_setting, _, parse, _ in CHANNELS
        if (getattr(settings, value_setting, "") or "").strip()
        and parse(getattr(settings, value_setting)) is None
    ]


# Каналы, где можно спросить цену: мессенджеры (кнопка «Узнать» у товара с ценой по запросу).
ASK_KINDS = (ContactKind.TELEGRAM, ContactKind.WHATSAPP)


def ask_links(message: str) -> list[Contact]:
    """Мессенджеры для вопроса о товаре. В WhatsApp сообщение подставляется в чат
    (параметр text), в Telegram ссылка ведёт в чат магазина без текста."""
    links = []
    for contact in get_contacts():
        if contact.kind not in ASK_KINDS:
            continue
        if contact.kind == ContactKind.WHATSAPP:
            contact = replace(contact, url=f"{contact.url}?text={quote(message)}")
        links.append(contact)
    return sorted(links, key=lambda c: ASK_KINDS.index(c.kind))
