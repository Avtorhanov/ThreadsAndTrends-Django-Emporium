"""Тексты и блоки витрины, которые администратор правит прямо на сайте."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.test import RequestFactory
from rest_framework.test import APIClient

from content import site
from content.contacts import ask_links, get_contacts
from content.models import Block, CustomizedArea, SiteText

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)


@pytest.fixture
def admin_api(staff):
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.fixture
def env_contacts(settings):
    settings.CONTACT_WHATSAPP = "+79001234567"
    settings.CONTACT_TELEGRAM = "@didishop"
    settings.CONTACT_VK = ""
    settings.SELLER_EMAIL = ""
    settings.SELLER_PHONE = ""


def render(source: str, user=None) -> str:
    request = RequestFactory().get("/")
    request.user = user or type("Anon", (), {"is_authenticated": False, "is_staff": False})()
    template = Template("{% load storefront %}" + source)
    return template.render(Context({"request": request}))


# --- Тексты ---


def test_text_default_override_and_hidden():
    source = '{% sitetext "footer.copy" %}DiDi-shop{% endsitetext %}'
    assert render(source) == "DiDi-shop"
    site.set_text("footer.copy", "Магазин <b>DiDi</b>")
    assert render(source) == "Магазин &lt;b&gt;DiDi&lt;/b&gt;"  # только текст, без разметки
    site.set_text("footer.copy", "")
    assert render(source) == ""
    site.reset_text("footer.copy")
    assert render(source) == "DiDi-shop"


def test_multiline_text_keeps_paragraphs():
    site.set_text("contacts.intro", "Первый абзац.\n\nВторой.")
    html = render('{% sitetext "contacts.intro" multiline %}По умолчанию{% endsitetext %}')
    assert html == "<p>Первый абзац.</p>\n\n<p>Второй.</p>"


def test_editor_markup_only_for_staff(staff):
    source = '{% sitetext "help.title" %}Помощь{% endsitetext %}'
    assert "data-text" not in render(source)
    assert render(source, staff) == '<span class="sx" data-text="help.title">Помощь</span>'
    site.set_text("help.title", "")
    assert 'class="sx sx--hidden" data-text="help.title"' in render(source, staff)


def test_text_key_and_length_are_validated():
    with pytest.raises(ValidationError):
        site.set_text("Bad Key!", "x")
    with pytest.raises(ValidationError):
        site.set_text("footer.copy", "x" * 2001)


def test_texts_are_cached_until_changed(django_assert_num_queries):
    site.set_text("a.b", "1")
    site.texts()
    with django_assert_num_queries(0):
        assert site.texts() == {"a.b": "1"}
    site.set_text("a.b", "2")
    assert site.texts() == {"a.b": "2"}


def test_text_api_requires_staff(client):
    assert client.put("/api/v1/admin/content/texts/footer.copy/", {}).status_code == 401
    customer = User.objects.create_user(email="c@example.com", password=PASSWORD)
    api = APIClient()
    api.force_login(customer)
    response = api.put("/api/v1/admin/content/texts/footer.copy/", {"value": "x"}, format="json")
    assert response.status_code == 403
    assert not SiteText.objects.exists()


def test_text_api_saves_hides_and_resets(admin_api):
    url = "/api/v1/admin/content/texts/footer.copy/"
    response = admin_api.put(url, {"value": "  Новый текст  "}, format="json")
    assert response.status_code == 200
    assert response.json() == {"key": "footer.copy", "value": "Новый текст"}
    assert admin_api.put(url, {"value": ""}, format="json").json()["value"] == ""
    assert admin_api.delete(url).status_code == 204
    assert not SiteText.objects.exists()
    bad = admin_api.put("/api/v1/admin/content/texts/Bad!/", {"value": "x"}, format="json")
    assert bad.status_code == 400


# --- Блоки ---


def test_defaults_until_customized(env_contacts):
    assert [b.title for b in site.blocks("help")][0] == "Доставка, оплата и возврат"
    assert all(b.pk is None for b in site.blocks("footer"))
    assert [c.kind for c in get_contacts()] == ["whatsapp", "telegram"]
    assert not Block.objects.exists()


def test_customize_copies_defaults_once(env_contacts, settings):
    blocks = site.customize("contacts")
    assert [(b.kind, b.value) for b in blocks] == [
        ("whatsapp", "+79001234567"),
        ("telegram", "@didishop"),
    ]
    site.customize("contacts")  # повтор — без дублей
    assert Block.objects.filter(area="contacts").count() == 2
    # Дальше контакты из БД: правка .env больше не влияет.
    settings.CONTACT_TELEGRAM = "@other"
    assert [c.handle for c in get_contacts()] == ["+7 900 123-45-67", "@didishop"]


def test_add_update_delete_and_reorder(env_contacts):
    vk = site.add_block(area="contacts", kind="vk", value="didishop", note="Сообщество")
    assert [c.kind for c in get_contacts()] == ["whatsapp", "telegram", "vk"]
    site.update_block(vk, value="vk.com/didi_shop")
    assert get_contacts()[2].url == "https://vk.com/didi_shop"
    whatsapp = Block.objects.get(area="contacts", kind="whatsapp")
    site.delete_block(whatsapp)
    ids = list(Block.objects.filter(area="contacts").values_list("pk", flat=True))
    site.reorder_blocks("contacts", list(reversed(ids)))
    assert [c.kind for c in get_contacts()] == ["vk", "telegram"]
    # «Узнать» у товара с ценой по запросу — оставшиеся мессенджеры.
    assert [c.kind for c in ask_links("?")] == ["telegram"]


def test_deleting_all_contacts_keeps_them_empty(env_contacts):
    for block in site.customize("contacts"):
        site.delete_block(block)
    assert get_contacts() == []
    assert CustomizedArea.objects.filter(area="contacts").exists()


@pytest.mark.parametrize(
    "value",
    ["javascript:alert(1)", "//evil.example", "data:text/html,x", "http://plain.example", ""],
)
def test_link_blocks_reject_unsafe_urls(value):
    with pytest.raises(ValidationError):
        site.add_block(area="help", title="Ссылка", value=value)


def test_link_blocks_accept_safe_urls():
    for value in ("/legal/delivery/", "https://t.me/didishop", "tel:+79001234567", "mailto:a@b.ru"):
        site.add_block(area="footer", title="Ссылка", value=value)
    assert Block.objects.filter(area="footer").count() == 3 + 4  # 3 по умолчанию + новые


def test_contact_block_value_is_validated():
    with pytest.raises(ValidationError) as exc:
        site.add_block(area="contacts", kind="telegram", value="not valid!")
    assert "value" in exc.value.message_dict
    with pytest.raises(ValidationError):
        site.add_block(area="contacts", kind="link", value="/x/")


def test_blocks_api(admin_api, env_contacts, client):
    listed = admin_api.get("/api/v1/admin/content/blocks/?area=help").json()
    assert [b["id"] for b in listed] == [None, None, None, None]
    ids = [
        b["id"]
        for b in admin_api.post(
            "/api/v1/admin/content/blocks/customize/", {"area": "help"}, format="json"
        ).json()
    ]
    assert all(ids)
    created = admin_api.post(
        "/api/v1/admin/content/blocks/",
        {"area": "help", "kind": "link", "title": "Размеры", "value": "/articles/razmery/"},
        format="json",
    )
    assert created.status_code == 201
    block_id = created.json()["id"]
    patched = admin_api.patch(
        f"/api/v1/admin/content/blocks/{block_id}/", {"title": "Размеры"}, format="json"
    )
    assert patched.json()["title"] == "Размеры"
    assert admin_api.delete(f"/api/v1/admin/content/blocks/{ids[0]}/").status_code == 204
    reordered = admin_api.post(
        "/api/v1/admin/content/blocks/reorder/",
        {"area": "help", "ids": [block_id, *ids[1:]]},
        format="json",
    ).json()
    assert reordered[0]["title"] == "Размеры"
    unsafe = admin_api.post(
        "/api/v1/admin/content/blocks/",
        {"area": "help", "kind": "link", "title": "x", "value": "javascript:alert(1)"},
        format="json",
    )
    assert unsafe.status_code == 400
    assert client.get("/api/v1/admin/content/blocks/?area=help").status_code == 401
