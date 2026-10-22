import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from content import services
from content.models import Article, ArticleImage
from store.management.commands.seed_demo import FIXTURE, IMAGES
from store.models import Product, ProductImage

from .factories import make_product

pytestmark = pytest.mark.django_db


def test_demo_fixture_is_consistent():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    manifest = json.loads((IMAGES / "manifest.json").read_text(encoding="utf-8"))
    product_slugs = {row["fields"]["slug"] for row in data if row["model"] == "store.product"}
    assert {entry["slug"] for entry in manifest} == product_slugs
    # Деньги — целые копейки.
    for row in data:
        if row["model"] == "store.product":
            assert isinstance(row["fields"]["price_kopecks"], int)


def test_seed_demo_loads_catalog_with_images_idempotently():
    call_command("seed_demo")
    products = Product.objects.live().count()
    images = ProductImage.objects.count()
    assert products >= 20
    expected = sum(1 for p in IMAGES.glob("*.jpg"))
    assert images == expected

    articles = Article.objects.published().count()
    assert articles == 3
    assert ArticleImage.objects.count() == 5

    call_command("seed_demo")  # повтор не дублирует фото и статьи
    assert ProductImage.objects.count() == images
    assert Product.objects.live().count() == products
    assert Article.objects.count() == articles


def test_seed_demo_keeps_own_articles():
    services.create_article(title="Своя статья")
    call_command("seed_demo")
    assert list(Article.objects.values_list("title", flat=True)) == ["Своя статья"]


def test_seed_demo_refuses_to_overwrite_own_products():
    make_product(name="Свой товар", slug="svoy-tovar")
    with pytest.raises(CommandError):
        call_command("seed_demo")
