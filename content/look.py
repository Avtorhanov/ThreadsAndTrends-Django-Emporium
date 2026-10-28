"""Оформление витрины для покупателя: палитра, акцент «Своей», углы, размер текста, тема.

Палитры и акценты — из content/palettes.json (генерирует scripts/gen_tokens.py из
tokens.json): значения от покупателя принимаются только из этого белого списка — они
попадают в атрибуты <html> и в CSS-селекторы. Администратор выбирает, какие палитры доступны
и что видит новый посетитель (ThemeSettings, панель → «Тема»).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from content.models import ThemeSettings

_DATA = json.loads(Path(__file__).with_name("palettes.json").read_text(encoding="utf-8"))
PALETTES: dict[str, dict] = {item["key"]: item for item in _DATA["palettes"]}
ACCENTS: dict[str, dict] = {item["key"]: item for item in _DATA["accents"]}
RADIUS: tuple[str, ...] = tuple(_DATA["radius"])
TEXT: tuple[str, ...] = tuple(_DATA["text"])
MODES = ("system", "light", "dark")

DEFAULT_PALETTE = "lime"
DEFAULT_ACCENT = next(iter(ACCENTS))
DEFAULT_RADIUS = "normal"
DEFAULT_TEXT = "s"
CUSTOM = "custom"

PALETTE_GROUPS = {"bright": "Яркие", "calm": "Сдержанные", "custom": "Свой цвет"}
RADIUS_LABELS = {"sharp": "Острые", "normal": "Средние", "soft": "Мягкие"}
TEXT_LABELS = {"s": "Обычный", "m": "Крупнее", "l": "Крупный"}
MODE_LABELS = {"system": "Как в системе", "light": "Светлая", "dark": "Тёмная"}
# Нижнее меню витрины на телефоне: сплошная полоса-футер, плавающая капсула, нижняя панель
# с подписями у всех вкладок.
NAV_LABELS = {"solid": "Сплошное", "floating": "Плавающее", "bar": "Нижняя панель"}
NAV: tuple[str, ...] = tuple(NAV_LABELS)
DEFAULT_NAV = "solid"

# Варианты для API (имена перечислений в схеме — SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES).
PALETTE_CHOICES = [(key, item["name"]) for key, item in PALETTES.items()]
PALETTE_GROUP_CHOICES = list(PALETTE_GROUPS.items())
MODE_CHOICES = list(MODE_LABELS.items())
RADIUS_CHOICES = [(key, RADIUS_LABELS[key]) for key in RADIUS]
TEXT_CHOICES = [(key, TEXT_LABELS[key]) for key in TEXT]
NAV_CHOICES = list(NAV_LABELS.items())

CACHE_KEY = "content:theme-settings:v3"

# Cookie личного выбора покупателя (пишут web/theme.py и site.js). Сохранение темы в панели
# удаляет их в браузере администратора — он сразу видит витрину как новый посетитель.
VISITOR_COOKIES = ("theme", "palette", "accent", "radius", "text_size")


@dataclass(frozen=True)
class ShopTheme:
    palettes: tuple[str, ...]
    default_palette: str
    default_mode: str
    default_radius: str
    nav_style: str = DEFAULT_NAV
    default_text: str = DEFAULT_TEXT


def _from_row(row: ThemeSettings | None) -> ShopTheme:
    if row is None:
        return ShopTheme(tuple(PALETTES), DEFAULT_PALETTE, "system", DEFAULT_RADIUS)
    # Палитру могли убрать из tokens.json — неизвестные ключи отбрасываются.
    palettes = tuple(key for key in row.palettes if key in PALETTES) or (DEFAULT_PALETTE,)
    default = row.default_palette if row.default_palette in palettes else palettes[0]
    mode = row.default_mode if row.default_mode in MODES else "system"
    radius = row.default_radius if row.default_radius in RADIUS else DEFAULT_RADIUS
    nav = row.nav_style if row.nav_style in NAV else DEFAULT_NAV
    text = row.default_text if row.default_text in TEXT else DEFAULT_TEXT
    return ShopTheme(palettes, default, mode, radius, nav, text)


def shop_theme() -> ShopTheme:
    value = cache.get(CACHE_KEY)
    if value is None:
        value = _from_row(ThemeSettings.objects.filter(pk=1).first())
        cache.set(CACHE_KEY, value, 60 * 60)
    return value


def get_row() -> ThemeSettings:
    row, _ = ThemeSettings.objects.get_or_create(pk=1)
    return row


@transaction.atomic
def update(
    *,
    palettes: list[str],
    default_palette: str,
    default_mode: str,
    default_radius: str,
    nav_style: str | None = None,
    default_text: str | None = None,
):
    unknown = [key for key in palettes if key not in PALETTES]
    if unknown:
        raise ValidationError({"palettes": f"Неизвестные палитры: {', '.join(unknown)}."})
    if not palettes:
        raise ValidationError({"palettes": "Оставьте покупателям хотя бы одну палитру."})
    if default_palette not in palettes:
        raise ValidationError(
            {"default_palette": "Палитра по умолчанию должна быть среди доступных."}
        )
    if default_mode not in MODES:
        raise ValidationError({"default_mode": "Неизвестная тема."})
    if default_radius not in RADIUS:
        raise ValidationError({"default_radius": "Неизвестный вариант углов."})
    if nav_style is not None and nav_style not in NAV:
        raise ValidationError({"nav_style": "Неизвестный вид нижнего меню."})
    if default_text is not None and default_text not in TEXT:
        raise ValidationError({"default_text": "Неизвестный размер текста."})
    row = get_row()
    # Порядок — как в tokens.json, без повторов.
    row.palettes = [key for key in PALETTES if key in set(palettes)]
    row.default_palette = default_palette
    row.default_mode = default_mode
    row.default_radius = default_radius
    if nav_style is not None:
        row.nav_style = nav_style
    if default_text is not None:
        row.default_text = default_text
    row.save()
    cache.delete(CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(CACHE_KEY))
    return row


@dataclass(frozen=True)
class Look:
    """Что видит покупатель: атрибуты <html> и цвет строки состояния (theme-color)."""

    palette: str
    accent: str
    radius: str
    text: str

    @property
    def attrs(self) -> dict[str, str]:
        """Атрибуты <html> (значения по умолчанию не пишутся — меньше разметки)."""
        attrs = {}
        if self.palette != DEFAULT_PALETTE:
            attrs["data-palette"] = self.palette
        if self.palette == CUSTOM:
            attrs["data-accent"] = self.accent
        if self.radius != DEFAULT_RADIUS:
            attrs["data-radius"] = self.radius
        if self.text != DEFAULT_TEXT:
            attrs["data-text"] = self.text
        return attrs

    @property
    def bg(self) -> dict[str, str]:
        return PALETTES[self.palette]["bg"]


def resolve_look(*, palette: str = "", accent: str = "", radius: str = "", text: str = "") -> Look:
    """Выбор покупателя → допустимые значения: недоступная палитра — палитра по умолчанию."""
    shop = shop_theme()
    return Look(
        palette=palette if palette in shop.palettes else shop.default_palette,
        accent=accent if accent in ACCENTS else DEFAULT_ACCENT,
        radius=radius if radius in RADIUS else shop.default_radius,
        text=text if text in TEXT else shop.default_text,
    )
