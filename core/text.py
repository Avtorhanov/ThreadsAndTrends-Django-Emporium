"""Текстовые утилиты без внешних зависимостей."""

from django.utils.text import slugify

# Транслитерация для URL (близко к правилам загранпаспорта / Яндекса).
_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def transliterate(value: str) -> str:
    return "".join(_TRANSLIT.get(char, char) for char in value.lower())


def slugify_ru(value: str, max_length: int = 200) -> str:
    """«Футболка белая» → «futbolka-belaya». Пустой результат — пустая строка."""
    slug = slugify(transliterate(value))[:max_length]
    return slug.strip("-")
