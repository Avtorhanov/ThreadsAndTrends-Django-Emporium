from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image
from rest_framework.test import APIClient

from content import services
from content.checks import contacts_are_valid
from content.contacts import get_contacts, telegram, vk, whatsapp
from content.models import Article, ArticleImage

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"


def image_file(size=(1200, 900)):
    buffer = BytesIO()
    Image.new("RGB", size, "green").save(buffer, "JPEG")
    return SimpleUploadedFile("x.jpg", buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture
def admin_client(db):
    staff = User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.fixture
def articles(db):
    published = services.create_article(
        title="Как выбрать размер",
        excerpt="Таблица размеров",
        body="Первый.\n\nВторой.",
        is_published=True,
    )
    draft = services.create_article(title="Черновик статьи")
    deleted = services.create_article(title="Удалённая статья", is_published=True)
    services.delete_article(deleted)
    return {"published": published, "draft": draft, "deleted": deleted}


# --- Сервис ---


def test_create_article_makes_slug_and_publication_date(articles):
    article = articles["published"]
    assert article.slug == "kak-vybrat-razmer"
    assert article.published_at is not None
    assert article.paragraphs == ["Первый.", "Второй."]
    assert articles["draft"].published_at is None


def test_slug_is_unique_including_deleted(articles):
    again = services.create_article(title="Удалённая статья")
    assert again.slug == "udalennaya-statya-2"


def test_slug_does_not_change_on_rename(articles):
    article = services.update_article(articles["published"], title="Размеры одежды")
    assert article.slug == "kak-vybrat-razmer"


def test_republish_keeps_first_date(articles):
    article = articles["published"]
    first = article.published_at
    services.update_article(article, is_published=False)
    article = services.update_article(article, is_published=True)
    assert article.published_at == first


def test_validation(db):
    with pytest.raises(ValidationError) as error:
        services.create_article(title="ab", excerpt="x" * 301)
    assert set(error.value.message_dict) == {"title", "excerpt"}
    with pytest.raises(ValidationError):
        services.create_article(title="Норм", slug="hack")


def test_deleted_article_cannot_be_edited_until_restored(articles):
    with pytest.raises(ValidationError):
        services.update_article(articles["deleted"], title="Новое имя")
    restored = services.restore_article(articles["deleted"])
    assert restored.deleted_at is None
    assert Article.objects.filter(pk=restored.pk).exists()


def test_images_limit_order_and_thumbnails(articles, django_capture_on_commit_callbacks):
    article = articles["published"]
    with django_capture_on_commit_callbacks(execute=True):
        images = [services.add_article_image(article, image_file()) for _ in range(6)]
    with pytest.raises(ValidationError):
        services.add_article_image(article, image_file())
    first = ArticleImage.objects.get(pk=images[0].pk)
    assert first.thumbs_ready and first.width == 1200
    assert first.image.name.startswith("articles/")
    reordered = services.reorder_article_images(article, [i.pk for i in reversed(images)])
    assert reordered[0].pk == images[-1].pk and reordered[0].position == 0
    with pytest.raises(ValidationError):
        services.reorder_article_images(article, [images[0].pk])


def test_not_an_image_is_rejected(articles):
    fake = SimpleUploadedFile("x.jpg", b"not an image", content_type="image/jpeg")
    with pytest.raises(ValidationError):
        services.add_article_image(articles["published"], fake)


def test_make_thumbnails_command_covers_articles(articles, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        image = services.add_article_image(articles["published"], image_file())
    ArticleImage.objects.filter(pk=image.pk).update(thumbs_ready=False)
    call_command("make_thumbnails")
    image.refresh_from_db()
    assert image.thumbs_ready


# --- Публичный API ---


def test_public_articles(client, articles):
    data = client.get("/api/v1/content/articles/").json()
    assert [item["slug"] for item in data] == ["kak-vybrat-razmer"]
    detail = client.get("/api/v1/content/articles/kak-vybrat-razmer/").json()
    assert detail["paragraphs"] == ["Первый.", "Второй."] and detail["images"] == []
    for key in ("draft", "deleted"):
        slug = articles[key].slug
        assert client.get(f"/api/v1/content/articles/{slug}/").status_code == 404


def test_public_articles_ignore_expired_jwt(client, articles):
    response = client.get("/api/v1/content/articles/", HTTP_AUTHORIZATION="Bearer expired.token")
    assert response.status_code == 200


def test_articles_query_count(client, articles, django_assert_max_num_queries):
    for n in range(5):
        services.create_article(title=f"Статья номер {n}", is_published=True)
    with django_assert_max_num_queries(2):
        client.get("/api/v1/content/articles/")


# --- Контакты ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("+7 (900) 123-45-67", ("https://wa.me/79001234567", "+7 900 123-45-67")),
        ("89001234567", ("https://wa.me/79001234567", "+7 900 123-45-67")),
        ("12", None),
    ],
)
def test_whatsapp_parsing(value, expected):
    assert whatsapp(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("@didishop", ("https://t.me/didishop", "@didishop")),
        ("https://t.me/didishop/", ("https://t.me/didishop", "@didishop")),
        ("javascript:alert(1)", None),
        ("bad name", None),
    ],
)
def test_telegram_parsing(value, expected):
    assert telegram(value) == expected


def test_vk_parsing():
    assert vk("https://vk.com/didi.shop") == ("https://vk.com/didi.shop", "vk.com/didi.shop")
    assert vk("didishop")[0] == "https://vk.com/didishop"
    assert vk("<script>") is None


def test_contacts_from_settings(settings, client):
    settings.CONTACT_WHATSAPP = "+79001234567"
    settings.CONTACT_TELEGRAM = "@didishop"
    settings.CONTACT_TELEGRAM_NOTE = "Наш канал"
    settings.CONTACT_VK = ""
    settings.SELLER_EMAIL = "shop@example.com"
    settings.SELLER_PHONE = ""
    kinds = [contact.kind for contact in get_contacts()]
    assert kinds == ["whatsapp", "telegram", "email"]
    data = client.get("/api/v1/content/contacts/").json()
    assert data[1] == {
        "kind": "telegram",
        "title": "Telegram",
        "url": "https://t.me/didishop",
        "handle": "@didishop",
        "note": "Наш канал",
    }


def test_invalid_contact_is_hidden_and_reported(settings):
    settings.CONTACT_TELEGRAM = "not valid!"
    assert get_contacts() == [] or all(c.kind != "telegram" for c in get_contacts())
    assert [warning.id for warning in contacts_are_valid(None)] == ["content.W001"]


# --- API панели ---


def test_admin_requires_staff(client, articles):
    assert client.get("/api/v1/admin/content/articles/").status_code == 401
    customer = User.objects.create_user(email="c@example.com", password=PASSWORD)
    api = APIClient()
    api.force_login(customer)
    assert api.get("/api/v1/admin/content/articles/").status_code == 403


def test_admin_list_filters(admin_client, articles):
    def slugs(**params):
        response = admin_client.get("/api/v1/admin/content/articles/", params)
        return {item["slug"] for item in response.json()["results"]}

    assert slugs() == {"kak-vybrat-razmer", "chernovik-stati"}
    assert slugs(status="draft") == {"chernovik-stati"}
    assert slugs(status="deleted") == {"udalennaya-statya"}
    assert slugs(search="размер") == {"kak-vybrat-razmer"}


def test_admin_crud_and_images(admin_client, django_capture_on_commit_callbacks):
    response = admin_client.post(
        "/api/v1/admin/content/articles/",
        {"title": "О магазине", "body": "Абзац", "is_published": True},
        format="json",
    )
    assert response.status_code == 201
    article = response.json()
    assert article["slug"] == "o-magazine" and article["published_at"]

    url = f"/api/v1/admin/content/articles/{article['id']}/"
    response = admin_client.patch(url, {"excerpt": "Коротко"}, format="json")
    assert response.json()["excerpt"] == "Коротко"

    with django_capture_on_commit_callbacks(execute=True):
        upload = admin_client.post(url + "images/", {"image": image_file()}, format="multipart")
    assert upload.status_code == 201
    image_id = upload.json()["id"]
    assert admin_client.get(url).json()["cover_url"].startswith("http://testserver/media/articles/")

    assert (
        admin_client.delete(f"/api/v1/admin/content/article-images/{image_id}/").status_code == 204
    )
    assert admin_client.delete(url).status_code == 204
    assert Article.all_objects.get(pk=article["id"]).is_deleted
    assert admin_client.post(url + "restore/").json()["deleted_at"] is None


def test_admin_validation_errors(admin_client):
    response = admin_client.post("/api/v1/admin/content/articles/", {"title": "ab"}, format="json")
    assert response.status_code == 400 and "title" in response.json()
