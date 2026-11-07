"""Таблица размеров обуви для страницы товара.

Размер варианта — строка; обувь панель записывает как «RU · US» («38 · 8 US»). Таблица —
та же, что в панели (admin-panel/src/components/catalog/sizes.ts, менять синхронно):
RU — общепринятая сетка, US — по длине стопы, как у Nike. None — у шкалы нет такого размера.
"""

from collections.abc import Iterable
from typing import NamedTuple


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
