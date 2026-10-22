import pytest
from django.core.management import call_command

from store.models import ProductImage
from store.services.catalog import add_product_image, delete_product_image
from store.services.images import thumb_name

from .conftest import image_file

pytestmark = pytest.mark.django_db


def upload(product, size, capture):
    with capture(execute=True):
        image = add_product_image(product, image_file(size=size))
    image.refresh_from_db()
    return image


def test_thumbnails_are_created_and_deleted(shop, django_capture_on_commit_callbacks):
    image = upload(shop["shirt"], (2000, 2500), django_capture_on_commit_callbacks)
    storage, name = image.image.storage, image.image.name
    assert storage.exists(thumb_name(name, 480)) and storage.exists(thumb_name(name, 960))
    assert [width for _, width in image.sources] == [480, 960, 2000]

    with django_capture_on_commit_callbacks(execute=True):
        delete_product_image(image)
    assert not storage.exists(name)
    assert not storage.exists(thumb_name(name, 480))


def test_small_photo_is_not_upscaled(shop, django_capture_on_commit_callbacks):
    image = upload(shop["shirt"], (600, 800), django_capture_on_commit_callbacks)
    storage = image.image.storage
    assert storage.exists(thumb_name(image.image.name, 480))
    assert not storage.exists(thumb_name(image.image.name, 960))
    assert [width for _, width in image.sources] == [480, 600]


def test_command_fills_missing_thumbnails(shop, django_capture_on_commit_callbacks):
    image = upload(shop["shirt"], (1000, 1000), django_capture_on_commit_callbacks)
    ProductImage.objects.filter(pk=image.pk).update(thumbs_ready=False, width=None, height=None)
    image.refresh_from_db()
    assert [width for _, width in image.sources] == [0]  # пока только оригинал, без srcset

    call_command("make_thumbnails")
    image.refresh_from_db()
    assert image.thumbs_ready and image.width == 1000
