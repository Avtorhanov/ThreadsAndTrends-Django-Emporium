"""Статьи: создание, правка, публикация, мягкое удаление, фото. Views (API панели) только
проверяют формат ввода и вызывают эти функции. Ошибки — ValidationError (→ 400)."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.text import slugify_ru
from store.services.catalog import inspect_image
from store.services.images import delete_thumbnails

from .models import Article, ArticleImage
from .tasks import make_article_image_thumbnails

MAX_IMAGES_PER_ARTICLE = 6
MAX_BODY_LENGTH = 20_000
EDITABLE_FIELDS = {"title", "excerpt", "body", "is_published"}


def _unique_slug(title: str, exclude_pk=None) -> str:
    base = slugify_ru(title, 200) or "article"
    slug, n = base, 2
    taken = Article.all_objects.all()
    if exclude_pk is not None:
        taken = taken.exclude(pk=exclude_pk)
    while taken.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _clean(fields: dict) -> dict:
    errors: dict[str, list[str]] = {}
    cleaned = {}
    if "title" in fields:
        title = " ".join(str(fields["title"] or "").split())
        if len(title) < 3:
            errors["title"] = ["Заголовок — не короче 3 символов."]
        elif len(title) > 200:
            errors["title"] = ["Заголовок — не длиннее 200 символов."]
        cleaned["title"] = title
    if "excerpt" in fields:
        excerpt = " ".join(str(fields["excerpt"] or "").split())
        if len(excerpt) > 300:
            errors["excerpt"] = ["Короткое описание — не длиннее 300 символов."]
        cleaned["excerpt"] = excerpt
    if "body" in fields:
        body = str(fields["body"] or "").replace("\r\n", "\n").strip()
        if len(body) > MAX_BODY_LENGTH:
            errors["body"] = [f"Текст — не длиннее {MAX_BODY_LENGTH} символов."]
        cleaned["body"] = body
    if "is_published" in fields:
        cleaned["is_published"] = bool(fields["is_published"])
    if errors:
        raise ValidationError(errors)
    return cleaned


def _apply_publication(article: Article) -> None:
    # Дата — при первой публикации; повторная публикация после снятия её не меняет.
    if article.is_published and article.published_at is None:
        article.published_at = timezone.now()


@transaction.atomic
def create_article(**fields) -> Article:
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}.")
    if "title" not in fields:
        raise ValidationError({"title": ["Укажите заголовок."]})
    cleaned = _clean(fields)
    article = Article(**cleaned, slug=_unique_slug(cleaned["title"]))
    _apply_publication(article)
    article.save()
    return article


def _locked(article: Article) -> Article:
    return Article.all_objects.select_for_update().get(pk=article.pk)


@transaction.atomic
def update_article(article: Article, **fields) -> Article:
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValidationError(f"Неизвестные поля: {', '.join(sorted(unknown))}.")
    article = _locked(article)
    if article.is_deleted:
        raise ValidationError("Статья удалена — сначала восстановите её.")
    cleaned = _clean(fields)
    for name, value in cleaned.items():
        setattr(article, name, value)
    _apply_publication(article)
    article.save()
    return article


@transaction.atomic
def delete_article(article: Article) -> Article:
    """Мягкое удаление: статья пропадает с сайта и из приложения, фото остаются (восстановление)."""
    article = _locked(article)
    if not article.is_deleted:
        article.deleted_at = timezone.now()
        article.save(update_fields=["deleted_at", "updated_at"])
    return article


@transaction.atomic
def restore_article(article: Article) -> Article:
    article = _locked(article)
    if article.is_deleted:
        article.deleted_at = None
        article.save(update_fields=["deleted_at", "updated_at"])
    return article


# --- Фото ---


@transaction.atomic
def add_article_image(article: Article, uploaded) -> ArticleImage:
    article = _locked(article)
    if article.is_deleted:
        raise ValidationError("Статья удалена — сначала восстановите её.")
    if ArticleImage.objects.filter(article=article).count() >= MAX_IMAGES_PER_ARTICLE:
        raise ValidationError({"image": f"Не больше {MAX_IMAGES_PER_ARTICLE} фото."})
    extension = inspect_image(uploaded)
    uploaded.name = f"upload{extension}"
    last = ArticleImage.objects.filter(article=article).aggregate(m=Max("position"))["m"]
    image = ArticleImage.objects.create(
        article=article, image=uploaded, position=0 if last is None else last + 1
    )
    transaction.on_commit(lambda: make_article_image_thumbnails.enqueue(image.pk))
    return image


@transaction.atomic
def delete_article_image(image: ArticleImage) -> None:
    storage, name = image.image.storage, image.image.name
    image.delete()
    transaction.on_commit(lambda: (storage.delete(name), delete_thumbnails(storage, name)))


@transaction.atomic
def reorder_article_images(article: Article, image_ids: list[int]) -> list[ArticleImage]:
    article = _locked(article)
    images = {image.pk: image for image in ArticleImage.objects.filter(article=article)}
    if len(image_ids) != len(set(image_ids)) or set(image_ids) != set(images):
        raise ValidationError({"ids": "Передайте все фото статьи, каждое один раз."})
    ordered = [images[pk] for pk in image_ids]
    for position, image in enumerate(ordered):
        image.position = position
    ArticleImage.objects.bulk_update(ordered, ["position"])
    return ordered
