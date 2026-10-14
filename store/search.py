"""Выражение полнотекстового поиска товаров. Отдельный модуль без импорта моделей:
его используют и индекс (store.models), и запросы витрины (store.services.storefront)."""

from django.contrib.postgres.search import SearchVector

# Русская морфология: «кроссовки», «кроссовок», «кроссовкам» находят друг друга.
SEARCH_CONFIG = "russian"


def search_vector() -> SearchVector:
    """Должно совпадать с выражением GIN-индекса product_search_idx, иначе Postgres
    не использует индекс. Название важнее описания (веса A и B)."""
    return SearchVector("name", weight="A", config=SEARCH_CONFIG) + SearchVector(
        "description", weight="B", config=SEARCH_CONFIG
    )
