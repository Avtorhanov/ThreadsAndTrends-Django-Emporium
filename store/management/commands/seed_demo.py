import json
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from store.models import Product
from store.services import catalog

FIXTURE = Path(settings.BASE_DIR) / "fixtures/catalog.json"
IMAGES = Path(settings.BASE_DIR) / "fixtures/demo_images"


def demo_slugs() -> set[str]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {row["fields"]["slug"] for row in data if row["model"] == "store.product"}


class Command(BaseCommand):
    help = (
        "Демо-каталог: категории, товары с размерами и остатками (fixtures/catalog.json) "
        "и фото (fixtures/demo_images). Повторный запуск безопасен: фото добавляются "
        "только товарам без фото."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Загрузить, даже если в каталоге есть недемонстрационные товары "
            "(перезапишет товары с теми же id)",
        )

    def handle(self, *args, force: bool, **options):
        own = Product.all_objects.exclude(slug__in=demo_slugs())
        if own.exists() and not force:
            raise CommandError(
                "В каталоге есть свои товары — демо-данные не загружены, чтобы их не перезаписать."
            )
        call_command("loaddata", str(FIXTURE), verbosity=0)

        manifest = json.loads((IMAGES / "manifest.json").read_text(encoding="utf-8"))
        added = 0
        for entry in manifest:
            product = Product.all_objects.filter(slug=entry["slug"]).first()
            if product is None or product.images.exists():
                continue
            for image in entry["images"]:
                path = IMAGES / image["file"]
                if not path.exists():
                    continue
                with path.open("rb") as fh:
                    catalog.add_product_image(product, File(fh, name=path.name))
                added += 1
        total = Product.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Демо-каталог: товаров {total}, новых фото {added}"))
