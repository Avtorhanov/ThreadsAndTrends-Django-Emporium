from django_tasks import task

from content.models import ArticleImage
from store.services.images import make_thumbnails


@task()
def make_article_image_thumbnails(image_id: int) -> None:
    """Уменьшенные копии нового фото статьи (воркер): загрузка в панели не ждёт обработки."""
    image = ArticleImage.objects.filter(pk=image_id).first()
    if image is not None:
        make_thumbnails(image)
