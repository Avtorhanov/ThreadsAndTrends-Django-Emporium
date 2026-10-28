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


def gif_file():
    buffer = BytesIO()
    frames = [Image.new("P", (300, 200), color) for color in (1, 2, 3)]
    frames[0].save(buffer, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    return SimpleUploadedFile("x.gif", buffer.getvalue(), content_type="image/gif")


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


def test_banner_images_listed_and_orphan_removed_on_publish(django_capture_on_commit_callbacks):
    banner = home.add_block("banner")
    with django_capture_on_commit_callbacks(execute=True):
        home.add_banner_image(banner, image_file())
        banner = home.add_banner_image(banner, image_file())
    first, second = (HomeImage.objects.get(pk=pk) for pk in banner.image_ids)
    # Порядок меняется, убранная картинка удаляется при публикации.
    banner = home.update_block(banner, image_ids=[second.pk, first.pk])
    assert banner.image_ids == [second.pk, first.pk]
    home.update_block(banner, image_ids=[second.pk])
    with pytest.raises(ValidationError):
        home.update_block(banner, image_ids=[second.pk, 99999])
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
        home.add_banner_image(text, image_file())


def test_banner_image_limit_and_gif(django_capture_on_commit_callbacks):
    banner = home.add_block("banner")
    with django_capture_on_commit_callbacks(execute=True):
        banner = home.add_banner_image(banner, gif_file())
    gif = HomeImage.objects.get(pk=banner.image_ids[0])
    # Анимация не превращается в неподвижные копии — витрина отдаёт оригинал.
    assert gif.image.name.endswith(".gif") and (gif.width, gif.height) == (300, 200)
    assert [url for url, _ in gif.sources] == [gif.image.url]
    for _ in range(home.MAX_BANNER_IMAGES - 1):
        banner = home.add_banner_image(banner, image_file())
    with pytest.raises(ValidationError):
        home.add_banner_image(banner, image_file())


def test_product_banner_uses_product_photos_and_link(client, django_capture_on_commit_callbacks):
    from store.services import catalog

    product = make_product("Термос Stanley", slug="termos")
    with django_capture_on_commit_callbacks(execute=True):
        catalog.add_product_image(product, image_file())
        catalog.add_product_image(product, image_file())
    banner = home.add_block("banner")
    home.update_block(banner, title="", text="", product=product)
    home.publish()

    block = home.published_blocks()[0]
    assert block.is_photo and len(block.images) == 2 and block.heading == "Термос Stanley"
    html = client.get("/").content.decode()
    assert 'class="hblock hblock-banner hblock-photo"' in html
    assert 'href="/product/termos/"' in html and "data-slides" in html
    public = APIClient().get(PUBLIC).json()["blocks"][0]
    assert public["product"]["slug"] == "termos" and len(public["images"]) == 2

    # Товар скрыли — баннер без своего текста и картинок пропадает.
    product.is_active = False
    product.save()
    assert home.published_blocks() == []


def test_consecutive_banners_become_carousel(client):
    for title in ("Первый", "Второй"):
        block = home.add_block("banner")
        home.update_block(block, title=title)
    home.add_block("text")
    single = home.add_block("banner")
    home.update_block(single, title="Отдельный")
    home.publish()
    rows = home.with_carousels(home.published_blocks())
    assert [row.kind for row in rows] == ["carousel", "text", "banner"]
    html = client.get("/").content.decode()
    assert html.count("data-carousel-dot") == 2 and "Отдельный" in html


def test_category_strip_custom_links(client):
    from content.models import Article

    clothes = make_category("Одежда", slug="clothes")
    article = Article.objects.create(
        title="Как выбрать размер",
        slug="size",
        body="Текст",
        is_published=True,
        published_at=timezone.now(),
    )
    strip = home.add_block("categories")
    links = [
        {"kind": "category", "id": clothes.pk},
        {"kind": "article", "id": article.pk, "title": "Размеры"},
        {"kind": "page", "key": "contacts"},
        {"kind": "url", "url": "https://t.me/didi", "title": "Telegram"},
    ]
    home.update_block(strip, links=links)
    home.publish()
    html = client.get("/").content.decode()
    for href, title in [
        ("/category/clothes/", "Одежда"),
        ("/articles/size/", "Размеры"),
        ("/contacts/", "Контакты"),
        ("https://t.me/didi", "Telegram"),
    ]:
        assert f'href="{href}"' in html and title in html
    public = APIClient().get(PUBLIC).json()["blocks"][0]["links"]
    assert [link["kind"] for link in public] == ["category", "article", "page", "url"]


@pytest.mark.parametrize(
    "link",
    [
        {"kind": "url", "url": "javascript:alert(1)", "title": "x"},
        {"kind": "url", "url": "//evil.example", "title": "x"},
        {"kind": "url", "url": "/ok/"},
        {"kind": "page", "key": "admin"},
        {"kind": "category", "id": 99999},
        {"kind": "nope"},
    ],
)
def test_category_strip_rejects_bad_links(link):
    strip = home.add_block("categories")
    with pytest.raises(ValidationError):
        home.update_block(strip, links=[link])


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
    assert upload.json()["image_url"] and len(upload.json()["images"]) == 1

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
