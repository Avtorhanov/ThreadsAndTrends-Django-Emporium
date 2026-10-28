import json
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from content import home
from content import services as content
from content.models import Article, HomeBlock
from store.models import Category, Product, ProductStatus
from store.services import catalog

FIXTURE = Path(settings.BASE_DIR) / "fixtures/catalog.json"
IMAGES = Path(settings.BASE_DIR) / "fixtures/demo_images"
ARTICLES = Path(settings.BASE_DIR) / "fixtures/demo_articles.json"

# Демо-статусы: какие товары витрина помечает. Префикс slug → название статуса из миграции.
DEMO_STATUSES = {
    "gucci-": "Под заказ",
    "kinder-advent-": "Ожидается поставка",
    "stanley-": "В наличии",
}


def demo_slugs() -> set[str]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return {row["fields"]["slug"] for row in data if row["model"] == "store.product"}


class Command(BaseCommand):
    help = (
        "Демо-каталог: категории, товары с размерами и остатками (fixtures/catalog.json) "
        "и фото (fixtures/demo_images), демо-статьи (fixtures/demo_articles.json). Повторный "
        "запуск безопасен: фото добавляются только товарам без фото, статьи — только если "
        "статей ещё нет."
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
        articles = self._seed_articles()
        self._seed_statuses()
        self._seed_home()
        total = Product.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Демо-каталог: товаров {total}, новых фото {added}, новых статей {articles}"
            )
        )

    def _seed_statuses(self) -> None:
        # Фикстура не знает о статусах; ставим только товарам без статуса — ручной выбор не трогаем.
        for prefix, name in DEMO_STATUSES.items():
            status = ProductStatus.objects.filter(name=name).first()
            if status is None:
                continue
            Product.all_objects.filter(slug__startswith=prefix, status__isnull=True).update(
                status=status
            )

    def _seed_home(self) -> None:
        # Демо-главная — только если владелец ещё не собирал свою.
        if HomeBlock.objects.exists() or home.get_page().published_at is not None:
            return
        by_slug = {c.slug: c for c in Category.objects.filter(slug__in=["dlya-doma", "luxe"])}
        banner = home.add_block("banner")
        home.update_block(
            banner,
            title="Новая коллекция",
            text="Термосы Stanley и вещи на осень — уже в каталоге",
            color="#DDF38A",
            category=by_slug.get("dlya-doma"),
        )
        # Второй баннер подряд — товар с фото: на витрине оба листаются каруселью.
        featured = (
            Product.objects.live().filter(images__isnull=False).order_by("-created_at").first()
        )
        if featured is not None:
            home.update_block(home.add_block("banner"), title="", text="", product=featured)
        home.update_block(home.add_block("categories"), title="Категории")
        home.update_block(home.add_block("collection"), title="Новинки")
        if "luxe" in by_slug:
            luxe = home.add_block("collection")
            home.update_block(luxe, title="LUXE", source="category", category=by_slug["luxe"])
        home.publish()

    def _seed_articles(self) -> int:
        # Статьи пишет владелец: демо-статьи — только в пустой раздел (свои не трогаем).
        if Article.all_objects.exists():
            return 0
        entries = json.loads(ARTICLES.read_text(encoding="utf-8"))
        # С конца: первая статья файла публикуется последней и стоит в списке первой.
        for entry in reversed(entries):
            article = content.create_article(
                title=entry["title"],
                excerpt=entry["excerpt"],
                body=entry["body"],
                is_published=True,
            )
            for file in entry["images"]:
                path = IMAGES / file
                if path.exists():
                    with path.open("rb") as fh:
                        content.add_article_image(article, File(fh, name=path.name))
        return len(entries)
