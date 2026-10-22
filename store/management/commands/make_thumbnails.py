from django.core.management.base import BaseCommand

from content.models import ArticleImage
from store.models import ProductImage
from store.services.images import make_thumbnails


class Command(BaseCommand):
    help = (
        "Уменьшенные копии фото товаров и статей для витрины (WebP 480/960 px). "
        "По умолчанию — только для фото без копий; --all пересоздаёт все."
    )

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Пересоздать копии у всех фото")

    def handle(self, *args, all: bool, **options):
        done = failed = 0
        for model in (ProductImage, ArticleImage):
            images = model.objects.order_by("pk")
            if not all:
                images = images.filter(thumbs_ready=False)
            for image in images.iterator(chunk_size=100):
                if make_thumbnails(image):
                    done += 1
                else:
                    failed += 1
        self.stdout.write(self.style.SUCCESS(f"Превью: готово {done}, с ошибкой {failed}"))
