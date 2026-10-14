"""Витрина: поиск, фильтры и сортировка публичного каталога, кэш дерева категорий."""

import re
from dataclasses import dataclass

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.cache import cache
from django.db.models import Exists, F, OuterRef, Prefetch, Q, QuerySet

from store.models import Category, Product, ProductVariant
from store.search import SEARCH_CONFIG, search_vector

MAX_QUERY_WORDS = 8
MAX_QUERY_LENGTH = 100

CATEGORY_TREE_CACHE_KEY = "catalog:category-tree:v1"
CATEGORY_TREE_CACHE_SECONDS = 60 * 60


class Sort:
    NEW = "new"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    RELEVANCE = "relevance"

    CHOICES = [
        (NEW, "Сначала новые"),
        (PRICE_ASC, "Сначала дешевле"),
        (PRICE_DESC, "Сначала дороже"),
        (RELEVANCE, "По релевантности (только с поиском)"),
    ]


def build_search_query(text: str) -> SearchQuery | None:
    """Поиск по началу слов («крос» → «кроссовки»): каждое слово — префикс, все слова обязательны.
    В tsquery попадают только буквы и цифры, поэтому синтаксис запроса не сломать."""
    words = re.findall(r"[^\W_]+", text.lower()[:MAX_QUERY_LENGTH])[:MAX_QUERY_WORDS]
    if not words:
        return None
    raw = " & ".join(f"{word}:*" for word in words)
    return SearchQuery(raw, search_type="raw", config=SEARCH_CONFIG)


def active_categories() -> QuerySet[Category]:
    return Category.objects.filter(is_active=True).filter(
        Q(parent__isnull=True) | Q(parent__is_active=True)
    )


@dataclass(frozen=True)
class ProductFilters:
    q: str = ""
    category: Category | None = None
    price_min: int | None = None  # копейки
    price_max: int | None = None  # копейки
    in_stock: bool = False
    sort: str = ""


def live_products() -> QuerySet[Product]:
    return Product.objects.live().with_stock().select_related("category").prefetch_related("images")


def filter_products(filters: ProductFilters) -> QuerySet[Product]:
    queryset = live_products()

    if filters.category is not None:
        # Корневая категория показывает товары всех своих подкатегорий.
        queryset = queryset.filter(
            Q(category=filters.category) | Q(category__parent=filters.category)
        )
    if filters.price_min is not None:
        queryset = queryset.filter(price_kopecks__gte=filters.price_min)
    if filters.price_max is not None:
        queryset = queryset.filter(price_kopecks__lte=filters.price_max)

    query = build_search_query(filters.q)
    # Поиск показывает только товары в наличии.
    if filters.in_stock or query is not None:
        queryset = queryset.filter(
            Exists(
                ProductVariant.objects.filter(
                    product=OuterRef("pk"), deleted_at__isnull=True, stock__gt=0
                )
            )
        )

    if query is not None:
        vector = search_vector()
        queryset = queryset.annotate(search=vector).filter(search=query)

    sort = filters.sort or (Sort.RELEVANCE if query is not None else Sort.NEW)
    # Последние ключи — стабильный порядок для пагинации при равных ценах и релевантности.
    if sort == Sort.PRICE_ASC:
        return queryset.order_by("price_kopecks", "-created_at", "-id")
    if sort == Sort.PRICE_DESC:
        return queryset.order_by("-price_kopecks", "-created_at", "-id")
    if sort == Sort.RELEVANCE and query is not None:
        return queryset.annotate(rank=SearchRank(F("search"), query)).order_by(
            "-rank", "-created_at", "-id"
        )
    return queryset.order_by("-created_at", "-id")


# --- Дерево категорий ---


def _build_category_tree() -> list[dict]:
    roots = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
        Prefetch("children", queryset=Category.objects.filter(is_active=True))
    )
    return [
        {
            "id": root.id,
            "slug": root.slug,
            "name": root.name,
            "children": [
                {"id": child.id, "slug": child.slug, "name": child.name}
                for child in root.children.all()
            ],
        }
        for root in roots
    ]


def category_tree() -> list[dict]:
    """Дерево активных категорий из общего кэша (CACHE_URL). Сбрасывается сигналами
    при любом изменении категорий (store.signals)."""
    tree = cache.get(CATEGORY_TREE_CACHE_KEY)
    if tree is None:
        tree = _build_category_tree()
        cache.set(CATEGORY_TREE_CACHE_KEY, tree, CATEGORY_TREE_CACHE_SECONDS)
    return tree


def invalidate_category_tree() -> None:
    cache.delete(CATEGORY_TREE_CACHE_KEY)
