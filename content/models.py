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


# --- Тексты и блоки витрины, которые администратор правит прямо на сайте ---


class SiteText(models.Model):
    """Текст витрины, изменённый администратором (двойное нажатие на сайте).

    Ключ — место в шаблоне (`{% sitetext "footer.copy" %}…{% endsitetext %}`), текст по
    умолчанию — в самом шаблоне. Пустое значение — текст скрыт; удаление записи возвращает
    исходный. Только обычный текст: при выводе экранируется.
    """

    key = models.CharField(max_length=80, unique=True, verbose_name="Ключ")
    value = models.TextField(blank=True, max_length=2000, verbose_name="Текст")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Изменён")

    class Meta:
        verbose_name = "Текст сайта"
        verbose_name_plural = "Тексты сайта"
        ordering = ["key"]

    def __str__(self):
        return self.key


class BlockArea(models.TextChoices):
    CONTACTS = "contacts", "Контакты"
    HELP = "help", "Помощь"
    FOOTER = "footer", "Подвал"


class BlockKind(models.TextChoices):
    LINK = "link", "Ссылка"
    WHATSAPP = "whatsapp", "WhatsApp"
    TELEGRAM = "telegram", "Telegram"
    VK = "vk", "ВКонтакте"
    PHONE = "phone", "Телефон"
    EMAIL = "email", "Почта"


class CustomizedArea(models.Model):
    """Раздел, который администратор уже менял: блоки берутся из БД, а не из настроек
    (.env для контактов) и значений по умолчанию. Запись создаётся при первом изменении."""

    area = models.CharField(max_length=20, choices=BlockArea.choices, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Изменённый раздел"
        verbose_name_plural = "Изменённые разделы"

    def __str__(self):
        return self.get_area_display()


class Block(models.Model):
    """Блок раздела витрины: канал связи в «Контактах», ссылка в «Помощи» или в подвале."""

    area = models.CharField(max_length=20, choices=BlockArea.choices, verbose_name="Раздел")
    kind = models.CharField(
        max_length=20, choices=BlockKind.choices, default=BlockKind.LINK, verbose_name="Тип"
    )
    title = models.CharField(max_length=80, blank=True, verbose_name="Название")
    # Ссылка (link) или значение канала: номер, @имя, адрес почты.
    value = models.CharField(max_length=300, verbose_name="Ссылка или значение")
    note = models.CharField(max_length=160, blank=True, verbose_name="Подпись")
    icon = models.CharField(max_length=20, blank=True, verbose_name="Значок")
    position = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Блок сайта"
        verbose_name_plural = "Блоки сайта"
        ordering = ["area", "position", "id"]
        indexes = [models.Index(fields=["area", "position"], name="block_area_position_idx")]

    def __str__(self):
        return f"{self.get_area_display()}: {self.title or self.value}"
