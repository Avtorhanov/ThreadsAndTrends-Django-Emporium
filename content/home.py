"""Главная из блоков: баннер, подборка товаров, лента категорий, текст.

Правки в панели — черновик (HomeBlock). «Опубликовать» сохраняет снимок видимых блоков в
HomePage.published — покупатель (сайт и приложение) видит только снимок. Товары подборок и
категории подставляются при показе: скрытый или удалённый товар пропадает сам.
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from content.models import (
    Article,
    CollectionSource,
    HomeBlock,
    HomeBlockKind,
    HomeImage,
    HomePage,
)
from store.models import Category, Product
from store.services.catalog import inspect_image
from store.services.images import delete_thumbnails
from store.services.storefront import (
    ProductFilters,
    active_categories,
    category_tree,
    filter_products,
    live_products,
)

from .tasks import make_home_image_thumbnails

K = HomeBlockKind

MAX_BLOCKS = 20
TITLE_MAX = 60
BANNER_TEXT_MAX = 120
TEXT_MAX = 1000
MAX_MANUAL_PRODUCTS = 12
COLLECTION_SIZE = 8
# Баннер: до 6 картинок (сменяют друг друга); у баннера товара без своих картинок — фото товара.
MAX_BANNER_IMAGES = 6
# Лента категорий: свои вкладки вместо корневых категорий.
MAX_LINKS = 12
LINK_TITLE_MAX = 40
LINK_URL_MAX = 300
LINK_KIND_CHOICES = [
    ("category", "Категория"),
    ("article", "Статья"),
    ("page", "Страница магазина"),
    ("url", "Ссылка"),
]
LINK_KINDS = tuple(key for key, _ in LINK_KIND_CHOICES)
# Страницы магазина для вкладок: ключ → (подпись по умолчанию, имя адреса).
LINK_PAGES = {
    "products": ("Все товары", "web:products"),
    "contacts": ("Контакты", "web:contacts"),
    "delivery": ("Доставка и оплата", "web:delivery"),
}
LINK_PAGE_CHOICES = [(key, title) for key, (title, _) in LINK_PAGES.items()]
CACHE_KEY = "content:home:v2"
# Тона баннера в панели; свой цвет — любой #RRGGBB.
BANNER_TONES = ("#DDF38A", "#FFE38F", "#C4EBD3", "#FFD6B0", "#7FA7CF", "#13261C")
INK_DARK, INK_LIGHT = "#13261C", "#FFFFFF"

HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
# Незакреплённая картинка (загрузили и сразу заменили) живёт сутки — вдруг вкладка ещё открыта.
ORPHAN_TTL = timedelta(days=1)

DEFAULTS: dict[str, dict] = {
    K.BANNER: {"title": "Новый баннер", "text": "Короткое описание", "color": "#FFE38F"},
    K.COLLECTION: {"title": "Подборка", "source": CollectionSource.NEW},
    K.CATEGORIES: {"title": "Категории"},
    K.TEXT: {"title": "Новый текст", "text": ""},
}

UPDATE_FIELDS = {
    "is_visible",
    "title",
    "text",
    "color",
    "category",
    "source",
    "product_ids",
    "image_ids",
    "product",
    "links",
}


def ink_for(color: str) -> str:
    """Цвет текста на фоне баннера — по относительной яркости (WCAG), чтобы надпись читалась."""
    if not HEX_COLOR.match(color or ""):
        return INK_DARK

    def channel(hex_part: str) -> float:
        value = int(hex_part, 16) / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(color[i : i + 2]) for i in (1, 3, 5))
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return INK_DARK if luminance > 0.18 else INK_LIGHT


# --- Черновик ---


def get_page() -> HomePage:
    page, _ = HomePage.objects.get_or_create(pk=1)
    return page


def has_changes(page: HomePage) -> bool:
    if page.changed_at is None:
        return False
    return page.published_at is None or page.changed_at > page.published_at


def draft_blocks() -> list[HomeBlock]:
    return list(HomeBlock.objects.select_related("category", "product"))


def _fresh(block: HomeBlock) -> HomeBlock:
    return HomeBlock.objects.select_related("category", "product").get(pk=block.pk)


def _touch() -> None:
    HomePage.objects.update_or_create(pk=1, defaults={"changed_at": timezone.now()})


def _clean_line(value: str) -> str:
    return " ".join((value or "").split())


def _clean_text(value: str) -> str:
    # Абзацы сохраняем (пустая строка — новый), лишние пробелы и пустые строки убираем.
    lines = [" ".join(line.split()) for line in (value or "").replace("\r\n", "\n").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


@transaction.atomic
def add_block(kind: str) -> HomeBlock:
    if kind not in K.values:
        raise ValidationError({"kind": "Неизвестный тип блока."})
    # Блокировка страницы: два параллельных добавления не займут одну позицию и не обойдут лимит.
    get_page()
    HomePage.objects.select_for_update().get(pk=1)
    if HomeBlock.objects.count() >= MAX_BLOCKS:
        raise ValidationError(f"На главной не больше {MAX_BLOCKS} блоков.")
    last = HomeBlock.objects.aggregate(m=Max("position"))["m"]
    block = HomeBlock.objects.create(
        kind=kind, position=0 if last is None else last + 1, **DEFAULTS[kind]
    )
    _touch()
    return block


@transaction.atomic
def update_block(block: HomeBlock, **changes) -> HomeBlock:
    unknown = set(changes) - UPDATE_FIELDS
    if unknown:
        raise ValueError(f"Неизвестные поля: {', '.join(sorted(unknown))}")
    block = HomeBlock.objects.select_for_update().get(pk=block.pk)
    if "image_ids" in changes:
        # Порядок и удаление — только среди уже загруженных картинок этого баннера.
        ids = list(changes["image_ids"] or [])
        if len(ids) != len(set(ids)) or not set(ids) <= set(block.image_ids or []):
            raise ValidationError({"image_ids": "Картинки — только из загруженных к баннеру."})
        changes["image_ids"] = ids
    for name, value in changes.items():
        setattr(block, name, value)
    _validate(block)
    block.save()
    _touch()
    return _fresh(block)


def _validate(block: HomeBlock) -> None:
    block.title = _clean_line(block.title)
    if len(block.title) > TITLE_MAX:
        raise ValidationError({"title": f"Заголовок — не больше {TITLE_MAX} символов."})

    if block.kind == K.BANNER:
        block.text = _clean_line(block.text)
        if len(block.text) > BANNER_TEXT_MAX:
            raise ValidationError({"text": f"Описание — не больше {BANNER_TEXT_MAX} символов."})
        block.color = (block.color or "").upper() or DEFAULTS[K.BANNER]["color"]
        if not HEX_COLOR.match(block.color):
            raise ValidationError({"color": "Цвет в формате #RRGGBB."})
        if not (block.title or block.text or block.image_ids or block.product_id):
            raise ValidationError(
                {"title": "У баннера нужен заголовок, описание, картинка или товар."}
            )
    elif block.kind == K.TEXT:
        block.text = _clean_text(block.text)
        if len(block.text) > TEXT_MAX:
            raise ValidationError({"text": f"Текст — не больше {TEXT_MAX} символов."})
    elif block.kind == K.COLLECTION:
        if block.source not in CollectionSource.values:
            raise ValidationError({"source": "Выберите, какие товары показывать."})
        if block.source == CollectionSource.CATEGORY and block.category_id is None:
            raise ValidationError({"category": "Выберите категорию."})
        ids = block.product_ids or []
        if len(ids) != len(set(ids)):
            raise ValidationError({"product_ids": "Товар добавлен дважды."})
        if len(ids) > MAX_MANUAL_PRODUCTS:
            raise ValidationError(
                {"product_ids": f"В подборке — не больше {MAX_MANUAL_PRODUCTS} товаров."}
            )
        if Product.objects.filter(pk__in=ids).count() != len(ids):
            raise ValidationError({"product_ids": "Товар не найден или удалён."})
        block.product_ids = list(ids)
    elif block.kind == K.CATEGORIES:
        block.links = _clean_links(block.links)


def _clean_links(links) -> list[dict]:
    """Вкладки ленты: категория, статья, страница магазина или адрес. Подпись необязательна
    (кроме адреса) — по умолчанию название категории, статьи или страницы."""
    if not isinstance(links, list):
        raise ValidationError({"links": "Список вкладок."})
    if len(links) > MAX_LINKS:
        raise ValidationError({"links": f"В ленте — не больше {MAX_LINKS} вкладок."})
    result = []
    for raw in links:
        if not isinstance(raw, dict) or raw.get("kind") not in LINK_KINDS:
            raise ValidationError({"links": "Неизвестный вид вкладки."})
        kind = raw["kind"]
        title = _clean_line(str(raw.get("title") or ""))
        if len(title) > LINK_TITLE_MAX:
            raise ValidationError({"links": f"Подпись — не больше {LINK_TITLE_MAX} символов."})
        item = {"kind": kind, "title": title}
        if kind in ("category", "article"):
            try:
                ref = int(raw.get("id"))
            except (TypeError, ValueError):
                raise ValidationError({"links": "Выберите категорию или статью."}) from None
            model = Category if kind == "category" else Article
            if not model.objects.filter(pk=ref).exists():
                raise ValidationError({"links": "Категория или статья не найдена."})
            item["id"] = ref
        elif kind == "page":
            if raw.get("key") not in LINK_PAGES:
                raise ValidationError({"links": "Неизвестная страница."})
            item["key"] = raw["key"]
        else:
            url = str(raw.get("url") or "").strip()
            # Только свой путь или https/http: значение попадает в href.
            if not re.match(r"^(/(?!/)|https?://)\S+$", url) or len(url) > LINK_URL_MAX:
                raise ValidationError({"links": "Адрес — путь на сайте (/…) или https://…"})
            if not title:
                raise ValidationError({"links": "У ссылки нужна подпись."})
            item["url"] = url
        result.append(item)
    return result


@transaction.atomic
def delete_block(block: HomeBlock) -> None:
    # Картинка баннера остаётся до публикации: её может показывать опубликованная главная.
    HomeBlock.objects.filter(pk=block.pk).delete()
    _touch()


@transaction.atomic
def reorder_blocks(ids: list[int]) -> list[HomeBlock]:
    get_page()
    HomePage.objects.select_for_update().get(pk=1)
    blocks = {block.pk: block for block in HomeBlock.objects.all()}
    if len(ids) != len(set(ids)) or set(ids) != set(blocks):
        raise ValidationError({"ids": "Передайте все блоки главной, каждый один раз."})
    ordered = [blocks[pk] for pk in ids]
    for position, block in enumerate(ordered):
        block.position = position
    HomeBlock.objects.bulk_update(ordered, ["position"])
    _touch()
    return draft_blocks()


@transaction.atomic
def add_banner_image(block: HomeBlock, uploaded) -> HomeBlock:
    """Картинка (JPEG, PNG, WebP или GIF) — в конец списка картинок баннера."""
    block = HomeBlock.objects.select_for_update().get(pk=block.pk)
    if block.kind != K.BANNER:
        raise ValidationError({"image": "Картинка есть только у баннера."})
    if len(block.image_ids or []) >= MAX_BANNER_IMAGES:
        raise ValidationError({"image": f"У баннера — не больше {MAX_BANNER_IMAGES} картинок."})
    extension = inspect_image(uploaded, allow_gif=True)
    # Имя от клиента не доверяем: путь строит home_image_path, расширение — по формату.
    uploaded.name = f"upload{extension}"
    image = HomeImage.objects.create(image=uploaded)
    block.image_ids = [*(block.image_ids or []), image.pk]
    block.save(update_fields=["image_ids", "updated_at"])
    _touch()
    transaction.on_commit(lambda: make_home_image_thumbnails.enqueue(image.pk))
    return _fresh(block)


@transaction.atomic
def remove_banner_images(block: HomeBlock) -> HomeBlock:
    block = HomeBlock.objects.select_for_update().get(pk=block.pk)
    block.image_ids = []
    _validate(block)
    block.save(update_fields=["image_ids", "updated_at"])
    _touch()
    return _fresh(block)


def snapshot_of(block: HomeBlock) -> dict:
    return {
        "id": block.pk,
        "kind": block.kind,
        "title": block.title,
        "text": block.text,
        "color": block.color,
        "image_ids": list(block.image_ids or []),
        "product_id": block.product_id,
        "category_id": block.category_id,
        "source": block.source,
        "product_ids": list(block.product_ids or []),
        "links": list(block.links or []),
    }


def _image_ids(item: dict) -> list[int]:
    # Снимки до картинок списком хранили одну картинку (image_id).
    if item.get("image_ids"):
        return list(item["image_ids"])
    return [item["image_id"]] if item.get("image_id") else []


@transaction.atomic
def publish() -> HomePage:
    get_page()
    page = HomePage.objects.select_for_update().get(pk=1)
    page.published = [snapshot_of(block) for block in draft_blocks() if block.is_visible]
    page.published_at = page.changed_at = timezone.now()
    page.save()
    _delete_orphan_images(page)
    # Сразу и после commit: параллельный запрос мог закэшировать снимок до фиксации.
    cache.delete(CACHE_KEY)
    transaction.on_commit(lambda: cache.delete(CACHE_KEY))
    return page


def _delete_orphan_images(page: HomePage) -> None:
    used = {pk for ids in HomeBlock.objects.values_list("image_ids", flat=True) for pk in ids or []}
    used |= {pk for item in page.published for pk in _image_ids(item)}
    orphans = list(
        HomeImage.objects.exclude(pk__in=used).filter(created_at__lt=timezone.now() - ORPHAN_TTL)
    )
    files = [(image.image.storage, image.image.name) for image in orphans]
    HomeImage.objects.filter(pk__in=[image.pk for image in orphans]).delete()

    def remove_files():
        for storage, name in files:
            storage.delete(name)
            delete_thumbnails(storage, name)

    # Файлы — только после фиксации: при откате записи и файлы целы.
    transaction.on_commit(remove_files)


# --- Показ покупателю ---


def published() -> tuple[list[dict], str]:
    """Снимок опубликованных блоков и его версия (для ключей кэша витрины)."""
    cached = cache.get(CACHE_KEY)
    if cached is None:
        row = HomePage.objects.filter(pk=1).values_list("published", "published_at").first()
        blocks, at = row if row else ([], None)
        cached = (blocks or [], at.isoformat() if at else "")
        cache.set(CACHE_KEY, cached, None)
    return cached


@dataclass
class ResolvedBlock:
    id: int
    kind: str
    title: str
    text: str
    color: str = ""
    ink: str = INK_DARK
    # Картинки баннера (HomeImage или фото товара — у обоих .sources) по порядку.
    images: list = field(default_factory=list)
    product: Product | None = None
    category: Category | None = None
    products: list[Product] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)
    # Лента категорий: [{"title", "url", "kind", "slug"}]
    links: list[dict] = field(default_factory=list)

    @property
    def image(self):
        return self.images[0] if self.images else None

    @property
    def is_photo(self) -> bool:
        """Фото-баннер (картинки или товар): фото в рамке карточки, текст поверх снизу."""
        return bool(self.images)

    @property
    def heading(self) -> str:
        return self.title or (self.product.name if self.product else "")

    @property
    def url(self) -> str:
        if self.product is not None:
            return reverse("web:product", args=[self.product.slug])
        if self.category is not None:
            return reverse("web:category", args=[self.category.slug])
        return ""

    @property
    def paragraphs(self) -> list[str]:
        return [part for part in self.text.split("\n\n") if part.strip()]


def resolve(items: list[dict], *, keep_empty: bool = False) -> list[ResolvedBlock]:
    """Снимок → блоки с данными. Пустые (подборка без товаров, категория выключена) покупателю
    не показываются; панели (keep_empty) нужны все — для предпросмотра."""
    image_ids = {pk for item in items for pk in _image_ids(item)}
    category_ids = {item["category_id"] for item in items if item.get("category_id")}
    product_ids = {item["product_id"] for item in items if item.get("product_id")}
    images = HomeImage.objects.in_bulk(image_ids) if image_ids else {}
    categories = active_categories().in_bulk(category_ids) if category_ids else {}
    products = live_products().in_bulk(product_ids) if product_ids else {}
    roots = None
    result = []
    for item in items:
        kind = item["kind"]
        category = categories.get(item.get("category_id"))
        block = ResolvedBlock(
            id=item["id"],
            kind=kind,
            title=item.get("title", ""),
            text=item.get("text", ""),
            category=category,
        )
        if kind == K.BANNER:
            block.color = item.get("color") or DEFAULTS[K.BANNER]["color"]
            block.ink = ink_for(block.color)
            block.product = products.get(item.get("product_id"))
            block.images = [images[pk] for pk in _image_ids(item) if pk in images]
            if not block.images and block.product is not None:
                photos = sorted(block.product.images.all(), key=lambda p: (p.position, p.pk))
                block.images = photos[:MAX_BANNER_IMAGES]
            if not (block.title or block.text or block.images) and not keep_empty:
                continue  # товар скрыт, а своего текста и картинок нет
        elif kind == K.COLLECTION:
            block.products = _collection(item, category)
            if not block.products and not keep_empty:
                continue
        elif kind == K.CATEGORIES:
            if roots is None:
                roots = category_tree()
            block.categories = roots
            block.links = _resolve_links(item.get("links") or [])
            if not (roots or block.links) and not keep_empty:
                continue
        elif kind == K.TEXT and not (block.title or block.text) and not keep_empty:
            continue
        result.append(block)
    return result


def _resolve_links(links: list[dict]) -> list[dict]:
    """Вкладки ленты → подпись и адрес. Выключенная категория или снятая статья пропадают."""
    if not links:
        return []
    category_ids = [link["id"] for link in links if link["kind"] == "category"]
    article_ids = [link["id"] for link in links if link["kind"] == "article"]
    categories = active_categories().in_bulk(category_ids) if category_ids else {}
    articles = Article.objects.published().in_bulk(article_ids) if article_ids else {}
    result = []
    for link in links:
        kind, title = link["kind"], link.get("title", "")
        if kind == "category":
            category = categories.get(link["id"])
            if category is None:
                continue
            url, title = reverse("web:category", args=[category.slug]), title or category.name
            result.append({"kind": kind, "title": title, "url": url, "slug": category.slug})
        elif kind == "article":
            article = articles.get(link["id"])
            if article is None:
                continue
            url, title = reverse("web:article", args=[article.slug]), title or article.title
            result.append({"kind": kind, "title": title, "url": url, "slug": article.slug})
        elif kind == "page":
            default, name = LINK_PAGES[link["key"]]
            result.append(
                {"kind": kind, "title": title or default, "url": reverse(name), "slug": link["key"]}
            )
        else:
            result.append({"kind": kind, "title": title, "url": link["url"], "slug": ""})
    return result


def _collection(item: dict, category: Category | None) -> list[Product]:
    source = item.get("source")
    if source == CollectionSource.MANUAL:
        ids = item.get("product_ids") or []
        found = {p.pk: p for p in live_products().filter(pk__in=ids)}
        return [found[pk] for pk in ids if pk in found]
    if source == CollectionSource.CATEGORY:
        if category is None:
            return []
        return list(filter_products(ProductFilters(category=category))[:COLLECTION_SIZE])
    return list(filter_products(ProductFilters())[:COLLECTION_SIZE])


@dataclass
class BannerRow:
    """Баннеры подряд — одна карусель: листаются сами и пальцем."""

    items: list[ResolvedBlock]
    kind: str = "carousel"


def with_carousels(blocks: list[ResolvedBlock]) -> list:
    rows: list = []
    for block in blocks:
        previous = rows[-1] if rows else None
        if block.kind == K.BANNER and previous is not None:
            if isinstance(previous, BannerRow):
                previous.items.append(block)
                continue
            if previous.kind == K.BANNER:
                rows[-1] = BannerRow([previous, block])
                continue
        rows.append(block)
    return rows


def published_blocks() -> list[ResolvedBlock]:
    items, _ = published()
    return resolve(items)
