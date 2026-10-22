"""Каталог витрины: главная, все товары, категория, поиск, карточка товара.

Выборка и сортировка — store.services.storefront (то же, что у API приложения). Готовые сетки
кэшируются (web.catalog_cache) — в них нет форм и данных пользователя.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from store.models import Category, Product, ProductImage, ProductVariant
from store.services.cart import max_quantity
from store.services.storefront import (
    ProductFilters,
    Sort,
    active_categories,
    filter_products,
)

from .. import catalog_cache
from ..forms import CatalogFilterForm
from ..seo import product_json_ld

PAGE_WINDOW = 2  # номеров страниц по обе стороны от текущей
EAGER_CARDS = 4


@dataclass(frozen=True)
class PageLink:
    number: int | None  # None — многоточие
    url: str = ""
    current: bool = False


def _rubles_param(kopecks: int | None) -> str:
    if kopecks is None:
        return ""
    rubles, rest = divmod(kopecks, 100)
    return f"{rubles},{rest:02d}" if rest else str(rubles)


def _params(values: dict, **changes) -> dict:
    """Нормализованные GET-параметры ленты (без мусора вроде utm — их нет в кэше сеток)."""
    params = {
        "q": values["q"],
        "price_min": _rubles_param(values["price_min"]),
        "price_max": _rubles_param(values["price_max"]),
        "in_stock": "1" if values["in_stock"] else "",
        "sort": values["sort"],
    }
    params.update(changes)
    return {key: value for key, value in params.items() if value not in ("", None)}


def _url(path: str, params: dict) -> str:
    return f"{path}?{urlencode(params)}" if params else path


def _page_links(page, path: str, values: dict) -> list[PageLink]:
    total = page.paginator.num_pages
    if total <= 1:
        return []
    numbers = sorted(
        {1, total} | set(range(page.number - PAGE_WINDOW, page.number + PAGE_WINDOW + 1))
    )
    links, previous = [], 0
    for number in numbers:
        if not 1 <= number <= total:
            continue
        if number - previous > 1:
            links.append(PageLink(None))
        params = _params(values, page=number if number > 1 else "")
        links.append(PageLink(number, _url(path, params), number == page.number))
        previous = number
    return links


def _paginate(queryset, raw: str):
    paginator = Paginator(queryset, settings.WEB_PAGE_SIZE)
    try:
        return paginator.page(raw)
    except (PageNotAnInteger, EmptyPage):
        # Несуществующая страница — 404, а не тихо первая: поисковик не плодит дубли.
        if raw in ("", "1"):
            return paginator.page(1)
        raise Http404("Такой страницы нет.") from None


def _grid(
    *, page_raw: str, cache_parts: tuple, queryset, path: str, values: dict, pages: bool = True
):
    """HTML сетки товаров с пагинацией (из кэша, если есть)."""
    cache_key = catalog_cache.key(*cache_parts, sorted(_params(values).items()), page_raw)

    def page_url(number: int) -> str:
        return _url(path, _params(values, page=number if number > 1 else ""))

    def render_grid() -> str:
        page = _paginate(queryset, page_raw)
        return render_to_string(
            "web/catalog/_grid.html",
            {
                "products": page.object_list,
                "page": page,
                "total": page.paginator.count,
                # Первый ряд карточек грузится сразу (LCP), остальные — лениво.
                "eager": EAGER_CARDS if page.number == 1 else 0,
                "page_links": _page_links(page, path, values) if pages else [],
                "prev_url": page_url(page.number - 1) if pages and page.has_previous() else "",
                "next_url": page_url(page.number + 1) if pages and page.has_next() else "",
                "more_url": "" if pages or not page.has_next() else path,
            },
        )

    # Кэш хранит строку: фрагмент собран нашим шаблоном (с экранированием) — вставляем как есть.
    return mark_safe(catalog_cache.get_or_render(cache_key, render_grid))


def _filtered(values: dict) -> bool:
    return any(values[name] for name in ("q", "price_min", "price_max", "in_stock", "sort"))


def _page_number(request) -> int:
    raw = request.GET.get("page", "1")
    return int(raw) if raw.isdigit() else 1


def home(request):
    values = CatalogFilterForm({}).values()
    # Главная — всегда первая страница новинок; дальше — «Весь каталог».
    grid = _grid(
        page_raw="1",
        cache_parts=("home",),
        queryset=filter_products(ProductFilters()),
        path=reverse("web:products"),
        values=values,
        pages=False,
    )
    return render(request, "web/catalog/home.html", {"grid": grid, "tab": "catalog"})


def _listing(request, *, category: Category | None, search: bool):
    values = CatalogFilterForm(request.GET).values()
    filters = ProductFilters(category=category, **values)
    if category is not None:
        path = reverse("web:category", args=[category.slug])
    else:
        path = reverse("web:search" if search else "web:products")
    page_number = _page_number(request)
    grid = _grid(
        page_raw=request.GET.get("page", "1"),
        cache_parts=("list", category.pk if category else "", search),
        queryset=filter_products(filters),
        path=path,
        values=values,
    )
    # Поиск и выборки с фильтрами не индексируются; страницы категории — с canonical на себя.
    noindex = search or _filtered(values)
    canonical = _url(path, {"page": page_number} if page_number > 1 else {})
    return render(
        request,
        "web/catalog/listing.html",
        {
            "grid": grid,
            "category": category,
            "root": category.parent if category and category.parent_id else category,
            "values": values,
            "price_min": _rubles_param(values["price_min"]),
            "price_max": _rubles_param(values["price_max"]),
            # Пустое значение — сортировка по умолчанию (с поиском — релевантность, без — новые).
            "default_sort": "По релевантности" if values["q"] else "Сначала новые",
            "sort_choices": [
                (value, label)
                for value, label in Sort.CHOICES
                if value != Sort.RELEVANCE and (value != Sort.NEW or values["q"])
            ],
            "search": search,
            "noindex": noindex,
            "canonical": canonical,
            "page_number": page_number,
            # Поиск — не вкладка: открывается из шапки, в нижней панели подсвечен «Каталог».
            "tab": "catalog",
            "filters_open": request.GET.get("filters") == "1" or _filtered(values),
        },
    )


def products(request):
    return _listing(request, category=None, search=False)


def search(request):
    return _listing(request, category=None, search=True)


def category(request, slug: str):
    found = get_object_or_404(active_categories().select_related("parent"), slug=slug)
    return _listing(request, category=found, search=False)


def product(request, slug: str):
    queryset = Product.objects.live().select_related("category", "category__parent")
    found = get_object_or_404(
        queryset.prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.order_by("position", "id")),
            Prefetch("variants", queryset=ProductVariant.objects.order_by("position", "id")),
        ),
        slug=slug,
    )
    variants = list(found.variants.all())
    sizes = [{"variant": variant, "available": max_quantity(variant) > 0} for variant in variants]
    in_stock = any(size["available"] for size in sizes)
    single = variants[0] if len(variants) == 1 and not variants[0].size else None
    images = list(found.images.all())
    return render(
        request,
        "web/catalog/product.html",
        {
            "product": found,
            "images": images,
            "sizes": sizes,
            "single_variant": single,
            "in_stock": in_stock,
            "json_ld": product_json_ld(request, found, images, in_stock),
            "tab": "catalog",
        },
    )
