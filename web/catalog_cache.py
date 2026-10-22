"""Кэш готовых сеток товаров (главная, категории).

Ключ включает «версию каталога»: любое изменение товара, варианта, фото или категории меняет
версию, и все сетки пересобираются. Остатки, списанные оформлением заказа (UPDATE без сигналов),
обновятся не позже WEB_CATALOG_CACHE_SECONDS — на карточке товара наличие всегда актуальное.
"""

import hashlib
import time

from django.conf import settings
from django.core.cache import cache

VERSION_KEY = "web:catalog-version"


def version() -> str:
    value = cache.get(VERSION_KEY)
    if value is None:
        value = str(time.time_ns())
        # add: параллельные запросы не перетирают версию, выставленную сбросом.
        cache.add(VERSION_KEY, value, None)
        value = cache.get(VERSION_KEY, value)
    return value


def bump() -> None:
    cache.set(VERSION_KEY, str(time.time_ns()), None)


def key(*parts) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f"web:grid:{version()}:{digest}"


def get_or_render(cache_key: str, render) -> str:
    html = cache.get(cache_key)
    if html is None:
        html = render()
        cache.set(cache_key, html, settings.WEB_CATALOG_CACHE_SECONDS)
    return html
