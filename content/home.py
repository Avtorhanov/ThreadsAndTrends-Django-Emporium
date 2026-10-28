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
from django.utils import timezone

from content.models import CollectionSource, HomeBlock, HomeBlockKind, HomeImage, HomePage
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
CACHE_KEY = "content:home:v1"
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

UPDATE_FIELDS = {"is_visible", "title", "text", "color", "category", "source", "product_ids"}


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
    return list(HomeBlock.objects.select_related("image", "category"))


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
    for name, value in changes.items():
        setattr(block, name, value)
    _validate(block)
    block.save()
    _touch()
    return HomeBlock.objects.select_related("image", "category").get(pk=block.pk)


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
        if not (block.title or block.text or block.image_id):
            raise ValidationError({"title": "У баннера нужен заголовок, описание или картинка."})
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
def set_banner_image(block: HomeBlock, uploaded) -> HomeBlock:
    block = HomeBlock.objects.select_for_update().get(pk=block.pk)
    if block.kind != K.BANNER:
        raise ValidationError({"image": "Картинка есть только у баннера."})
    extension = inspect_image(uploaded)
    # Имя от клиента не доверяем: путь строит home_image_path, расширение — по формату.
    uploaded.name = f"upload{extension}"
    image = HomeImage.objects.create(image=uploaded)
    block.image = image
    block.save(update_fields=["image", "updated_at"])
    _touch()
    transaction.on_commit(lambda: make_home_image_thumbnails.enqueue(image.pk))
    return HomeBlock.objects.select_related("image", "category").get(pk=block.pk)


@transaction.atomic
def remove_banner_image(block: HomeBlock) -> HomeBlock:
    block = HomeBlock.objects.select_for_update().get(pk=block.pk)
    block.image = None
    _validate(block)
    block.save(update_fields=["image", "updated_at"])
    _touch()
    return HomeBlock.objects.select_related("image", "category").get(pk=block.pk)


def snapshot_of(block: HomeBlock) -> dict:
    return {
        "id": block.pk,
        "kind": block.kind,
        "title": block.title,
        "text": block.text,
        "color": block.color,
        "image_id": block.image_id,
        "category_id": block.category_id,
        "source": block.source,
        "product_ids": list(block.product_ids or []),
    }


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
    used = set(HomeBlock.objects.exclude(image=None).values_list("image_id", flat=True))
    used |= {item["image_id"] for item in page.published if item.get("image_id")}
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
    image: HomeImage | None = None
    category: Category | None = None
    products: list[Product] = field(default_factory=list)
    categories: list[dict] = field(default_factory=list)

    @property
    def paragraphs(self) -> list[str]:
        return [part for part in self.text.split("\n\n") if part.strip()]


def resolve(items: list[dict], *, keep_empty: bool = False) -> list[ResolvedBlock]:
    """Снимок → блоки с данными. Пустые (подборка без товаров, категория выключена) покупателю
    не показываются; панели (keep_empty) нужны все — для предпросмотра."""
    image_ids = {item["image_id"] for item in items if item.get("image_id")}
    category_ids = {item["category_id"] for item in items if item.get("category_id")}
    images = HomeImage.objects.in_bulk(image_ids) if image_ids else {}
    categories = active_categories().in_bulk(category_ids) if category_ids else {}
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
            block.image = images.get(item.get("image_id"))
        elif kind == K.COLLECTION:
            block.products = _collection(item, category)
            if not block.products and not keep_empty:
                continue
        elif kind == K.CATEGORIES:
            if roots is None:
                roots = category_tree()
            block.categories = roots
            if not roots and not keep_empty:
                continue
        elif kind == K.TEXT and not (block.title or block.text) and not keep_empty:
            continue
        result.append(block)
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


def published_blocks() -> list[ResolvedBlock]:
    items, _ = published()
    return resolve(items)
