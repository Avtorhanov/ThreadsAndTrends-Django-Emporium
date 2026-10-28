"""Главная из блоков: черновик → публикация, проверка блоков, API, показ на сайте."""

from datetime import timedelta
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from content import home
from content.models import HomeBlock, HomeImage
from store.tests.factories import make_category, make_product

pytestmark = pytest.mark.django_db

User = get_user_model()
ADMIN = "/api/v1/admin/content/home/"
PUBLIC = "/api/v1/content/home/"


def image_file():
    buffer = BytesIO()
    Image.new("RGB", (1200, 600), "orange").save(buffer, "JPEG")
    return SimpleUploadedFile("x.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture
def admin_api(db):
    staff = User.objects.create_user(
        email="staff@example.com", password="x-Pass-12345", is_staff=True
    )
    client = APIClient()
    client.force_login(staff)
    return client


def test_draft_is_invisible_until_published():
    banner = home.add_block("banner")
    home.update_block(banner, title="Осенняя коллекция", text="Уже в каталоге")
    assert home.published() == ([], "")
    assert home.has_changes(home.get_page())

    home.publish()
    items, version = home.published()
    assert [item["title"] for item in items] == ["Осенняя коллекция"] and version
    assert not home.has_changes(home.get_page())

    home.update_block(banner, title="Зимняя коллекция")
    assert home.published()[0][0]["title"] == "Осенняя коллекция"
    assert home.has_changes(home.get_page())


def test_hidden_blocks_are_not_published():
    shown, hidden = home.add_block("text"), home.add_block("text")
    home.update_block(shown, text="Доставка за 1–3 дня")
    home.update_block(hidden, is_visible=False)
    home.publish()
    assert [item["id"] for item in home.published()[0]] == [shown.pk]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"title": "я" * 61}, "title"),
        ({"text": "я" * 121}, "text"),
        ({"color": "red; background: url(x)"}, "color"),
        ({"title": "", "text": ""}, "title"),
    ],
)
def test_banner_validation(changes, field):
    banner = home.add_block("banner")
    with pytest.raises(ValidationError) as error:
        home.update_block(banner, **changes)
    assert field in error.value.message_dict


def test_banner_text_color_follows_background():
    assert home.ink_for("#DDF38A") == home.INK_DARK
    assert home.ink_for("#13261C") == home.INK_LIGHT
    assert home.ink_for("#2F5D8A") == home.INK_LIGHT


def test_collection_sources():
    clothes = make_category("Одежда", slug="clothes")
    shirt = make_product("Рубашка", category=clothes)
    cap = make_product("Кепка")
    hidden = make_product("Скрытая", is_active=False)

    block = home.add_block("collection")
    with pytest.raises(ValidationError):
        home.update_block(block, source="category", category=None)
    home.update_block(block, source="category", category=clothes)
    assert home.resolve([home.snapshot_of(HomeBlock.objects.get(pk=block.pk))])[0].products == [
        shirt
    ]

    home.update_block(block, source="manual", product_ids=[cap.pk, hidden.pk, shirt.pk])
    resolved = home.resolve([home.snapshot_of(HomeBlock.objects.get(pk=block.pk))])
    # Скрытый товар в подборку не попадает; порядок — как выбрал администратор.
    assert resolved[0].products == [cap, shirt]
    with pytest.raises(ValidationError):
        home.update_block(block, product_ids=[cap.pk, cap.pk])


def test_empty_collection_hidden_from_customer():
    block = home.add_block("collection")
    snapshot = [home.snapshot_of(block)]
    assert home.resolve(snapshot) == []
    assert len(home.resolve(snapshot, keep_empty=True)) == 1


def test_reorder_requires_all_blocks():
    first, second = home.add_block("text"), home.add_block("banner")
    assert [b.pk for b in home.reorder_blocks([second.pk, first.pk])] == [second.pk, first.pk]
    with pytest.raises(ValidationError):
        home.reorder_blocks([second.pk])


def test_banner_image_replaced_and_orphan_removed_on_publish(django_capture_on_commit_callbacks):
    banner = home.add_block("banner")
    with django_capture_on_commit_callbacks(execute=True):
        first = home.set_banner_image(banner, image_file()).image
        second = home.set_banner_image(banner, image_file()).image
    assert first.pk != second.pk
    # Свежая незакреплённая картинка живёт сутки (вкладка панели могла её ещё показывать).
    HomeImage.objects.filter(pk=first.pk).update(created_at=timezone.now() - timedelta(days=2))
    storage, name = first.image.storage, first.image.name
    with django_capture_on_commit_callbacks(execute=True):
        home.publish()
    assert not HomeImage.objects.filter(pk=first.pk).exists()
    assert not storage.exists(name)
    assert HomeImage.objects.filter(pk=second.pk).exists()


def test_image_only_for_banner():
    text = home.add_block("text")
    with pytest.raises(ValidationError):
        home.set_banner_image(text, image_file())


# --- API ---


def test_admin_api_flow(admin_api):
    created = admin_api.post(f"{ADMIN}blocks/", {"kind": "banner"}, format="json")
    assert created.status_code == 201, created.content
    pk = created.json()["id"]

    patched = admin_api.patch(
        f"{ADMIN}blocks/{pk}/", {"title": "Распродажа", "color": "#13261c"}, format="json"
    )
    assert patched.status_code == 200, patched.content
    assert (patched.json()["color"], patched.json()["ink"]) == ("#13261C", home.INK_LIGHT)

    upload = admin_api.post(
        f"{ADMIN}blocks/{pk}/image/", {"image": image_file()}, format="multipart"
    )
    assert upload.status_code == 200, upload.content
    assert upload.json()["image_url"]

    state = admin_api.get(ADMIN).json()
    assert state["has_changes"] is True and state["published_at"] is None

    published = admin_api.post(f"{ADMIN}publish/")
    assert published.status_code == 200 and published.json()["has_changes"] is False

    public = APIClient().get(PUBLIC).json()["blocks"]
    assert [(b["kind"], b["title"], b["ink"]) for b in public] == [
        ("banner", "Распродажа", home.INK_LIGHT)
    ]
    assert public[0]["image_url"].startswith("http://testserver/")

    assert admin_api.delete(f"{ADMIN}blocks/{pk}/").status_code == 204
    assert admin_api.get(ADMIN).json()["has_changes"] is True


def test_admin_api_rejects_customer(db):
    customer = User.objects.create_user(email="c@example.com", password="x-Pass-12345")
    client = APIClient()
    client.force_login(customer)
    assert client.get(ADMIN).status_code == 403
    assert client.post(f"{ADMIN}publish/").status_code == 403


def test_public_collection_has_products(db):
    product = make_product("Термос")
    block = home.add_block("collection")
    home.update_block(block, title="Новинки")
    home.publish()
    blocks = APIClient().get(PUBLIC).json()["blocks"]
    assert blocks[0]["products"][0]["slug"] == product.slug


def test_storefront_renders_published_blocks(client):
    clothes = make_category("Одежда", slug="clothes")
    make_product("Рубашка", category=clothes)
    banner = home.add_block("banner")
    home.update_block(banner, title="Новая коллекция", category=clothes)
    home.add_block("collection")
    text = home.add_block("text")
    home.update_block(text, title="Доставка", text="Курьером по городу.\n\nСамовывоз — бесплатно.")
    home.publish()

    html = client.get("/").content.decode()
    assert 'class="hblock hblock-banner"' in html and "Новая коллекция" in html
    assert 'href="/category/clothes/"' in html
    assert "hblock-rail" in html and "Рубашка" in html
    assert "<p>Курьером по городу.</p>" in html and "Все товары" in html


def test_storefront_without_blocks_unchanged(client):
    make_product("Рубашка")
    html = client.get("/").content.decode()
    assert "home-blocks" not in html and "Рубашка" in html
