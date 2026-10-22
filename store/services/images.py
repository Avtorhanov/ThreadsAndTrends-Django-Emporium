"""Уменьшенные копии фото для витрины (WebP 480 и 960 px по ширине): фото товаров
(store.ProductImage) и статей (content.ArticleImage) — у обеих моделей поля image, width,
height, thumbs_ready.

Оригинал (до 5 МБ) остаётся как есть; копии лежат рядом: products/2026/10/<uuid>.w480.webp.
Создаются фоновой задачей после загрузки фото (store.tasks.make_image_thumbnails), для уже
загруженных — `manage.py make_thumbnails`. Пока копий нет, витрина показывает оригинал.
"""

import logging
from io import BytesIO
from pathlib import PurePosixPath

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

THUMB_WIDTHS = (480, 960)
WEBP_QUALITY = 80


def thumb_name(name: str, width: int) -> str:
    path = PurePosixPath(name)
    return str(path.with_name(f"{path.stem}.w{width}.webp"))


def _widths_for(image) -> list[int]:
    # Копия шире оригинала не нужна: браузер возьмёт оригинал.
    return [w for w in THUMB_WIDTHS if image.width and w < image.width]


def thumb_sources(image) -> list[tuple[str, int]]:
    storage = image.image.storage
    sources = []
    if image.thumbs_ready:
        sources = [(storage.url(thumb_name(image.image.name, w)), w) for w in _widths_for(image)]
    sources.append((image.image.url, image.width or 0))
    return sources


def make_thumbnails(image) -> bool:
    """Создать копии и записать размеры оригинала. Повторный вызов перезаписывает копии."""
    storage = image.image.storage
    try:
        with storage.open(image.image.name, "rb") as fh, Image.open(fh) as source:
            # Ориентация из EXIF (фото с телефона), затем RGB/RGBA — WebP не умеет CMYK и палитры.
            picture = ImageOps.exif_transpose(source)
            picture = picture.convert("RGBA" if picture.mode in ("RGBA", "LA", "P") else "RGB")
            width, height = picture.size
            image.width, image.height = width, height
            for target in _widths_for(image):
                copy = picture.resize(
                    (target, max(1, round(height * target / width))), Image.Resampling.LANCZOS
                )
                buffer = BytesIO()
                copy.save(buffer, "WEBP", quality=WEBP_QUALITY, method=4)
                name = thumb_name(image.image.name, target)
                if storage.exists(name):
                    storage.delete(name)
                storage.save(name, ContentFile(buffer.getvalue()))
    except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
        logger.warning("Превью для фото %s не созданы: %s", image.pk, exc)
        return False
    image.thumbs_ready = True
    # save (а не update): сигнал post_save сбрасывает кэш сеток витрины — там появятся копии.
    image.save(update_fields=["width", "height", "thumbs_ready"])
    return True


def delete_thumbnails(storage, name: str) -> None:
    for width in THUMB_WIDTHS:
        storage.delete(thumb_name(name, width))
