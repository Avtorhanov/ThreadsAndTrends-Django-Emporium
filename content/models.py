"""Статьи магазина (вкладка «Контакты»): о магазине, выбор размера, уход за вещами.

Пишет и публикует администратор в панели. Текст — обычные абзацы без HTML (пустая строка —
новый абзац), поэтому в статью нельзя внедрить разметку или скрипт.
"""

import uuid
from pathlib import PurePosixPath

from django.db import models
from django.db.models import Q
from django.utils import timezone


class ArticleQuerySet(models.QuerySet):
    def published(self):
        """Видны покупателям: опубликованы и не удалены."""
        return self.filter(is_published=True, deleted_at__isnull=True)


class ArticleManager(models.Manager.from_queryset(ArticleQuerySet)):
    """Без удалённых. Все статьи, включая удалённые, — Article.all_objects."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Article(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    # Транслит заголовка; уникален среди всех статей, включая удалённые; при смене заголовка
    # не меняется (ссылки из поисковиков не ломаются).
    slug = models.SlugField(max_length=220, unique=True, verbose_name="Slug")
    excerpt = models.CharField(max_length=300, blank=True, verbose_name="Короткое описание")
    body = models.TextField(blank=True, verbose_name="Текст")
    is_published = models.BooleanField(default=False, verbose_name="Опубликована")
    # Дата первой публикации: по ней порядок в списке и дата на странице статьи.
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Опубликована")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменена")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Удалена")

    objects = ArticleManager()
    all_objects = models.Manager.from_queryset(ArticleQuerySet)()

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        ordering = ["-published_at", "-id"]
        indexes = [
            models.Index(
                fields=["-published_at"],
                name="article_published_idx",
                condition=Q(is_published=True, deleted_at__isnull=True),
            ),
            models.Index(fields=["-created_at"], name="article_created_idx"),
        ]

    def __str__(self):
        return self.title

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def cover(self):
        """Первое фото — обложка; использует prefetch, если он есть."""
        images = list(self.images.all())
        return images[0] if images else None

    @property
    def paragraphs(self) -> list[str]:
        return [
            part.strip() for part in self.body.replace("\r\n", "\n").split("\n\n") if part.strip()
        ]


def article_image_path(instance, filename):
    # Имя файла от клиента не используется: только расширение, путь — UUID.
    ext = PurePosixPath(filename).suffix.lower() or ".jpg"
    return f"articles/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class ArticleImage(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="images", verbose_name="Статья"
    )
    image = models.ImageField(upload_to=article_image_path, verbose_name="Изображение")
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Загружено")
    # Как у фото товаров (store.services.images): размеры оригинала и готовность превью WebP.
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name="Ширина, px")
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name="Высота, px")
    thumbs_ready = models.BooleanField(default=False, verbose_name="Превью готовы")

    class Meta:
        verbose_name = "Фото статьи"
        verbose_name_plural = "Фото статей"
        ordering = ["position", "id"]

    def __str__(self):
        return f"{self.article} #{self.position}"

    @property
    def sources(self) -> list[tuple[str, int]]:
        from store.services.images import thumb_sources

        return thumb_sources(self)
