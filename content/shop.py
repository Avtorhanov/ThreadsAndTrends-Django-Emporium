"""Настройки магазина (панель → «Настройки»): доставка, оплата, реквизиты продавца.

Значения хранит одна строка ShopSettings; пустое поле — значение из настроек сервера (.env),
поэтому до первого сохранения магазин работает как раньше. Действующие значения — current()
(строка БД в общем кэше до следующего сохранения, .env подставляется при каждом чтении).

Способы оформления: онлайн-оплата ЮKassa (переключатель действует, только если ЮKassa подключена
в .env — ORDERS_ONLINE_PAYMENT_ENABLED и ключи; ключи в панель не попадают), согласование
с продавцом в мессенджере (канал — из контактов магазина), оплата при получении. Хотя бы один
способ остаётся всегда: если выключено всё доступное — согласование.

Не зависит от DRF: ошибки — django ValidationError.
"""

import re
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from content.models import ShopSettings
from core.choices import AgreementChannel

CACHE_KEY = "content:shop-settings:v2"
CACHE_SECONDS = 60 * 60
MAX_DELIVERY_KOPECKS = 100_000_00
MAX_FREE_FROM_KOPECKS = 10_000_000_00
TIMEOUT_RANGE = (10, 24 * 60)
AGREEMENT_TIMEOUT_RANGE = (1, 14 * 24)

# Поля строки настроек, которые меняет панель.
FIELDS = (
    "delivery_courier_kopecks",
    "delivery_free_from_kopecks",
    "pickup_enabled",
    "pickup_address",
    "cash_on_delivery_enabled",
    "online_payment_enabled",
    "agreement_enabled",
    "agreement_channel",
    "unpaid_timeout_minutes",
    "agreement_timeout_hours",
    "seller_name",
    "seller_inn",
    "seller_ogrn",
    "seller_address",
    "seller_phone",
    "seller_email",
)
SELLER_FIELDS = ("name", "inn", "ogrn", "address", "phone", "email")
_TRAILING = re.compile(r"[\s,;:·]+$")


def clean_text(value: str) -> str:
    """Пробелы по краям и двойные убираются, хвостовые запятые и точки с запятой — тоже:
    реквизиты собираются в одну строку через « · ». Точка остаётся (инициалы «И. И.»)."""
    return _TRAILING.sub("", " ".join((value or "").split()))


@dataclass(frozen=True)
class SellerPart:
    text: str
    href: str = ""


@dataclass(frozen=True)
class Seller:
    name: str = ""
    inn: str = ""
    ogrn: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""

    @property
    def ogrn_label(self) -> str:
        # 13 цифр — ОГРН юрлица, 15 — ОГРНИП индивидуального предпринимателя.
        return "ОГРН" if len(re.sub(r"\D", "", self.ogrn)) == 13 else "ОГРНИП"

    def parts(self) -> list[SellerPart]:
        """Заполненные реквизиты по порядку — одна строка подвала; пустые не показываются."""
        parts = []
        if self.name:
            parts.append(SellerPart(self.name))
        if self.inn:
            parts.append(SellerPart(f"ИНН {self.inn}"))
        if self.ogrn:
            parts.append(SellerPart(f"{self.ogrn_label} {self.ogrn}"))
        if self.address:
            parts.append(SellerPart(self.address))
        if self.phone:
            digits = re.sub(r"[^\d+]", "", self.phone)
            parts.append(SellerPart(self.phone, f"tel:{digits}" if digits else ""))
        if self.email:
            parts.append(SellerPart(self.email, f"mailto:{self.email}"))
        return parts


@dataclass(frozen=True)
class Shop:
    """Действующие настройки: значение из панели или, если поле пустое, из .env."""

    delivery_courier_kopecks: int
    delivery_free_from_kopecks: int
    # Пусто — самовывоза нет (выключен или адрес не задан ни в панели, ни в .env).
    pickup_address: str
    cash_on_delivery: bool
    online_payment: bool
    agreement: bool
    agreement_channel: str
    unpaid_timeout_minutes: int
    agreement_timeout_hours: int
    seller: Seller


def _row_values() -> dict | None:
    """Значения строки настроек (None — ещё не сохранялись), в общем кэше."""
    values = cache.get(CACHE_KEY)
    if values is None:
        row = ShopSettings.objects.filter(pk=1).values(*FIELDS).first()
        values = {"row": row}
        cache.set(CACHE_KEY, values, CACHE_SECONDS)
    return values["row"]


def env_defaults() -> dict:
    """Значения из .env — подсказка в пустых полях панели."""
    return {
        "delivery_courier_kopecks": settings.DELIVERY_COURIER_KOPECKS,
        "delivery_free_from_kopecks": settings.DELIVERY_FREE_FROM_KOPECKS,
        "pickup_address": settings.PICKUP_ADDRESS,
        "unpaid_timeout_minutes": settings.ORDERS_UNPAID_TIMEOUT_MINUTES,
        "agreement_timeout_hours": settings.ORDERS_AGREEMENT_TIMEOUT_HOURS,
        "seller_name": settings.SELLER_NAME,
        "seller_inn": settings.SELLER_INN,
        "seller_ogrn": settings.SELLER_OGRN,
        "seller_address": settings.SELLER_ADDRESS,
        "seller_phone": settings.SELLER_PHONE,
        "seller_email": settings.SELLER_EMAIL,
    }


def online_payment_available() -> bool:
    """ЮKassa подключена на сервере (.env)."""
    return bool(settings.ORDERS_ONLINE_PAYMENT_ENABLED)


def _methods(row: dict) -> tuple[bool, bool, bool]:
    """(онлайн, согласование, при получении) с учётом подключения ЮKassa. Онлайн-оплата
    до первого сохранения настроек (NULL) — как в .env."""
    online_switch = row.get("online_payment_enabled")
    online = online_payment_available() and (online_switch is None or bool(online_switch))
    agreement = bool(row.get("agreement_enabled", True))
    cash = bool(row.get("cash_on_delivery_enabled", False))
    if not (online or agreement or cash):
        agreement = True  # без способа оформления покупатель не сможет заказать
    return online, agreement, cash


def current() -> Shop:
    row = _row_values() or {}
    env = env_defaults()

    def pick(field: str):
        value = row.get(field)
        return env[field] if value in (None, "") else value

    pickup_enabled = row.get("pickup_enabled", True)
    online, agreement, cash = _methods(row)
    return Shop(
        delivery_courier_kopecks=pick("delivery_courier_kopecks"),
        delivery_free_from_kopecks=pick("delivery_free_from_kopecks"),
        pickup_address=clean_text(pick("pickup_address")) if pickup_enabled else "",
        cash_on_delivery=cash,
        online_payment=online,
        agreement=agreement,
        agreement_channel=row.get("agreement_channel") or AgreementChannel.WHATSAPP,
        unpaid_timeout_minutes=pick("unpaid_timeout_minutes"),
        agreement_timeout_hours=pick("agreement_timeout_hours"),
        seller=Seller(**{name: clean_text(pick(f"seller_{name}")) for name in SELLER_FIELDS}),
    )


def get_row() -> ShopSettings:
    """Строка для панели (несохранённая — значения по умолчанию)."""
    return ShopSettings.objects.filter(pk=1).first() or ShopSettings()


def _invalidate() -> None:
    cache.delete(CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(CACHE_KEY))


def _validate(values: dict) -> dict:
    errors: dict[str, str] = {}
    cleaned = dict(values)

    for field, maximum in (
        ("delivery_courier_kopecks", MAX_DELIVERY_KOPECKS),
        ("delivery_free_from_kopecks", MAX_FREE_FROM_KOPECKS),
    ):
        value = cleaned.get(field)
        if value is not None and not 0 <= value <= maximum:
            errors[field] = f"От 0 до {maximum // 100:,} ₽.".replace(",", " ")

    timeout = cleaned.get("unpaid_timeout_minutes")
    if timeout is not None and not TIMEOUT_RANGE[0] <= timeout <= TIMEOUT_RANGE[1]:
        errors["unpaid_timeout_minutes"] = (
            f"От {TIMEOUT_RANGE[0]} до {TIMEOUT_RANGE[1]} минут (сутки)."
        )

    for field in ("pickup_address", "seller_name", "seller_address"):
        cleaned[field] = clean_text(cleaned.get(field, ""))

    inn = re.sub(r"\D", "", cleaned.get("seller_inn", ""))
    if cleaned.get("seller_inn", "").strip() and len(inn) not in (10, 12):
        errors["seller_inn"] = "ИНН — 10 цифр (организация) или 12 (ИП)."
    cleaned["seller_inn"] = inn

    ogrn = re.sub(r"\D", "", cleaned.get("seller_ogrn", ""))
    if cleaned.get("seller_ogrn", "").strip() and len(ogrn) not in (13, 15):
        errors["seller_ogrn"] = "ОГРН — 13 цифр, ОГРНИП — 15."
    cleaned["seller_ogrn"] = ogrn

    phone = " ".join(cleaned.get("seller_phone", "").split())
    if phone and (
        re.search(r"[^\d\s()+\-]", phone) or not 10 <= len(re.sub(r"\D", "", phone)) <= 15
    ):
        errors["seller_phone"] = "Телефон: цифры, пробелы, скобки и дефис — +7 900 123-45-67."
    cleaned["seller_phone"] = phone

    email = cleaned.get("seller_email", "").strip().lower()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors["seller_email"] = "Неверный адрес почты."
    cleaned["seller_email"] = email

    hours = cleaned.get("agreement_timeout_hours")
    if hours is not None and not AGREEMENT_TIMEOUT_RANGE[0] <= hours <= AGREEMENT_TIMEOUT_RANGE[1]:
        errors["agreement_timeout_hours"] = (
            f"От {AGREEMENT_TIMEOUT_RANGE[0]} до {AGREEMENT_TIMEOUT_RANGE[1]} часов (2 недели)."
        )

    if cleaned.get("agreement_channel") not in AgreementChannel.values:
        errors["agreement_channel"] = "Выберите канал: WhatsApp, Telegram, ВКонтакте или телефон."

    switch = cleaned.get("online_payment_enabled")
    online = online_payment_available() and (switch is None or bool(switch))
    if not (
        online or cleaned.get("agreement_enabled", True) or cleaned.get("cash_on_delivery_enabled")
    ):
        errors["agreement_enabled"] = (
            "Включите хотя бы один способ оформления — иначе покупатель не сможет заказать."
        )

    if errors:
        raise ValidationError(errors)
    return cleaned


@transaction.atomic
def update(**values) -> ShopSettings:
    """Сохранить настройки целиком (все поля FIELDS)."""
    unknown = set(values) - set(FIELDS)
    if unknown:
        raise ValueError(f"Неизвестные поля настроек: {sorted(unknown)}")
    row = ShopSettings.objects.select_for_update().filter(pk=1).first() or ShopSettings(pk=1)
    current_values = {field: getattr(row, field) for field in FIELDS}
    cleaned = _validate({**current_values, **values})
    for field, value in cleaned.items():
        setattr(row, field, value)
    row.save()
    _invalidate()
    return row
