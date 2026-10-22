from django_tasks import task

from store.models import ProductImage
from store.services.images import make_thumbnails


@task()
def make_image_thumbnails(image_id: int) -> None:
    """Уменьшенные копии нового фото (воркер): загрузка в панели не ждёт обработки."""
    image = ProductImage.objects.filter(pk=image_id).first()
    if image is not None:
        make_thumbnails(image)
