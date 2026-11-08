"""Таблица размеров обуви для страницы товара.

Размер варианта — строка; обувь панель записывает как «RU · US» («38 · 8 US»). Таблица —
та же, что в панели (admin-panel/src/components/catalog/sizes.ts, менять синхронно):
RU — общепринятая сетка, US — по длине стопы, как у Nike. None — у шкалы нет такого размера.
"""

import re
from collections.abc import Iterable
from decimal import Decimal
from typing import NamedTuple

SIZE_SEPARATOR = " · "
CLOTHING_ORDER = ("XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL")
_NUMERIC_SIZE = re.compile(r"^(\d+(?:[.,]\d+)?)( US)?$")


class ShoeRow(NamedTuple):
    ru: int
    cm: str
    women: str | None
    men: str | None


SHOE_CHART: tuple[ShoeRow, ...] = (
    ShoeRow(35, "22,5", "5,5", None),
    ShoeRow(36, "23", "6", None),
    ShoeRow(37, "24", "7,5", None),
    ShoeRow(38, "24,5", "8", "6,5"),
    ShoeRow(39, "25", "8,5", "7"),
    ShoeRow(40, "26", "10", "8"),
    ShoeRow(41, "26,5", "10,5", "9"),
    ShoeRow(42, "27", "11", "9,5"),
    ShoeRow(43, "28", None, "10,5"),
    ShoeRow(44, "28,5", None, "11"),
    ShoeRow(45, "29", None, "12"),
    ShoeRow(46, "30", None, "13"),
)


def has_shoe_sizes(sizes: Iterable[str]) -> bool:
    """Есть размер обуви в US («8 US», «38 · 8 US») — показать таблицу размеров."""
    return any(size.endswith(" US") for size in sizes)


def size_group(size: str) -> str:
    """Значение фильтра: у обуви — только RU («38 · 8 US» → «38»), остальные — как записаны."""
    return size.split(SIZE_SEPARATOR, 1)[0].strip()


def _size_sort_key(size: str) -> tuple[int, Decimal, str]:
    if size in CLOTHING_ORDER:
        return 0, Decimal(CLOTHING_ORDER.index(size)), ""
    number = _NUMERIC_SIZE.match(size)
    if number:
        return (2 if number[2] else 1), Decimal(number[1].replace(",", ".")), ""
    return 3, Decimal(0), size.casefold()


def sort_sizes(sizes: Iterable[str]) -> list[str]:
    """Порядок чипов: буквенные по сетке, числа по возрастанию, затем «8 US», затем прочие."""
    return sorted(set(sizes), key=_size_sort_key)
