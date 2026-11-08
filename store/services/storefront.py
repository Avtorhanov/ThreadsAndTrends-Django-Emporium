"""Витрина: поиск, фильтры и сортировка публичного каталога, кэш дерева категорий."""

import re
from collections.abc import Iterable
from dataclasses import dataclass, replace

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.cache import cache
from django.db.models import Case, Exists, F, IntegerField, OuterRef, Prefetch, Q, QuerySet, When

from store.models import Category, Product, ProductVariant
from store.search import SEARCH_CONFIG, search_vector
from store.sizes import SIZE_SEPARATOR, size_group, sort_sizes

MAX_QUERY_WORDS = 8
MAX_QUERY_LENGTH = 100
MAX_FILTER_SIZES = 30
MAX_SIZE_LENGTH = 50

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
    sizes: tuple[str, ...] = ()  # значения clean_sizes


def live_products() -> QuerySet[Product]:
    return (
        Product.objects.live()
        .with_stock()
        .select_related("category", "status")
        .prefetch_related("images")
    )


def clean_sizes(values: Iterable[str]) -> tuple[str, ...]:
    """Параметры size из запроса: значения фильтра без пустых, повторов и лишнего."""
    groups = {size_group(value)[:MAX_SIZE_LENGTH] for value in values}
    groups.discard("")
    return tuple(sort_sizes(groups)[:MAX_FILTER_SIZES])


def _stocked_variants() -> QuerySet[ProductVariant]:
    return ProductVariant.objects.filter(deleted_at__isnull=True, stock__gt=0)


def _size_condition(sizes: Iterable[str]) -> Q:
    condition = Q()
    for size in sizes:
        condition |= Q(size=size) | Q(size__startswith=f"{size}{SIZE_SEPARATOR}")
    return condition


def _apply_filters(
    queryset: QuerySet[Product], filters: ProductFilters, query: SearchQuery | None
) -> QuerySet[Product]:
    if filters.category is not None:
        # Корневая категория показывает товары всех своих подкатегорий.
        queryset = queryset.filter(
            Q(category=filters.category) | Q(category__parent=filters.category)
        )
    if filters.price_min is not None:
        queryset = queryset.filter(price_kopecks__gte=filters.price_min)
    if filters.price_max is not None:
        queryset = queryset.filter(price_kopecks__lte=filters.price_max)

    stocked = _stocked_variants().filter(product=OuterRef("pk"))
    if filters.sizes:
        queryset = queryset.filter(Exists(stocked.filter(_size_condition(filters.sizes))))
    # Поиск показывает только товары в наличии.
    elif filters.in_stock or query is not None:
        queryset = queryset.filter(Exists(stocked))

    if query is not None:
        queryset = queryset.annotate(search=search_vector()).filter(search=query)
    return queryset


def filter_products(filters: ProductFilters) -> QuerySet[Product]:
    query = build_search_query(filters.q)
    queryset = _apply_filters(live_products(), filters, query)

    sort = filters.sort or (Sort.RELEVANCE if query is not None else Sort.NEW)
    # Последние ключи — стабильный порядок для пагинации при равных ценах и релевантности.
    # Товары с ценой по запросу — в конце при любой сортировке по цене.
    if sort == Sort.PRICE_ASC:
        return queryset.order_by(F("price_kopecks").asc(nulls_last=True), "-created_at", "-id")
    if sort == Sort.PRICE_DESC:
        return queryset.order_by(F("price_kopecks").desc(nulls_last=True), "-created_at", "-id")
    if sort == Sort.RELEVANCE and query is not None:
        return queryset.annotate(rank=SearchRank(F("search"), query)).order_by(
            "-rank", "-created_at", "-id"
        )
    return queryset.order_by("-created_at", "-id")


def available_sizes(filters: ProductFilters) -> list[str]:
    """Значения фильтра по текущей выборке. Сам выбор размера её не сужает: иначе после
    отметки одного размера остальные чипы исчезли бы. Один запрос при любом числе товаров."""
    products = _apply_filters(
        Product.objects.live(), replace(filters, sizes=()), build_search_query(filters.q)
    )
    sizes = (
        _stocked_variants()
        .filter(product__in=products.values("pk"))
        .exclude(size="")
        .order_by()
        .values_list("size", flat=True)
        .distinct()
    )
    return sort_sizes(size_group(size) for size in sizes)


# --- Похожие товары ---

SIMILAR_LIMIT = 12


def similar_products(product: Product, limit: int = SIMILAR_LIMIT) -> list[Product]:
    """«Похожие» на карточке товара: сначала та же категория, затем соседние подкатегории
    того же корня; внутри — товары в наличии первыми, затем новые."""
    category = product.category
    root_id = category.parent_id or category.pk
    queryset = (
        live_products()
        .exclude(pk=product.pk)
        .filter(Q(category_id=root_id) | Q(category__parent_id=root_id))
        .annotate(
            same_category=Case(
                When(category_id=category.pk, then=0), default=1, output_field=IntegerField()
            ),
            available=Case(When(total_stock__gt=0, then=0), default=1, output_field=IntegerField()),
        )
        .order_by("same_category", "available", "-created_at", "-id")
    )
    return list(queryset[:limit])


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
