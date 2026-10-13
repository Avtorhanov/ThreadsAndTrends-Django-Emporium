"""Форматирование копеек в шаблонах: {{ product.price_kopecks|rub }} → «55 000» / «1 234,50»."""

from django import template

register = template.Library()

NBSP = " "


def format_kopecks(kopecks) -> str:
    if kopecks in (None, ""):
        return ""
    kopecks = int(kopecks)
    sign = "-" if kopecks < 0 else ""
    rubles, rest = divmod(abs(kopecks), 100)
    whole = f"{rubles:,}".replace(",", NBSP)
    return f"{sign}{whole},{rest:02d}" if rest else f"{sign}{whole}"


@register.filter
def rub(kopecks):
    return format_kopecks(kopecks)


@register.filter
def rub_times(kopecks, quantity):
    """Сумма строки: цена в копейках × количество."""
    return format_kopecks(int(kopecks or 0) * int(quantity or 0))
