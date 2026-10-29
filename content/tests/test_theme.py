"""Тема для покупателей: палитры из tokens.json, выбор администратора, cookie на сайте, API."""

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from content import look

pytestmark = pytest.mark.django_db

User = get_user_model()
TOKENS = Path(settings.BASE_DIR) / "docs/design/lime-tech/tokens.json"
ADMIN = "/api/v1/admin/content/theme/"


@pytest.fixture
def admin_api(db):
    staff = User.objects.create_user(
        email="staff@example.com", password="x-Pass-12345", is_staff=True
    )
    client = APIClient()
    client.force_login(staff)
    return client


def configure(palettes, default, mode="system", radius="normal"):
    return look.update(
        palettes=palettes, default_palette=default, default_mode=mode, default_radius=radius
    )


def test_whitelist_matches_tokens():
    tokens = json.loads(TOKENS.read_text(encoding="utf-8"))
    assert list(look.PALETTES) == [k for k in tokens["palettes"] if k != "comment"]
    assert list(look.ACCENTS) == [k for k in tokens["accents"] if k != "comment"]
    assert len(look.ACCENTS) == 14


def test_defaults_without_settings():
    theme = look.shop_theme()
    assert theme.palettes == tuple(look.PALETTES) and theme.default_palette == "lime"
    assert look.resolve_look().attrs == {}


def test_unknown_values_fall_back():
    chosen = look.resolve_look(palette="neon", accent="<script>", radius="round", text="xl")
    assert (chosen.palette, chosen.accent, chosen.radius, chosen.text) == (
        "lime",
        look.DEFAULT_ACCENT,
        "normal",
        "s",
    )


def test_update_validates_default_and_list():
    with pytest.raises(ValidationError):
        configure([], "lime", "system", "normal")
    with pytest.raises(ValidationError):
        look.update(
            palettes=["steel"],
            default_palette="lime",
            default_mode="system",
            default_radius="normal",
        )
    look.update(
        palettes=["steel", "lime"],
        default_palette="steel",
        default_mode="dark",
        default_radius="soft",
    )
    theme = look.shop_theme()
    # Порядок — как в tokens.json, независимо от порядка в запросе.
    assert theme.palettes == ("lime", "steel") and theme.default_palette == "steel"
    assert (theme.default_mode, theme.default_radius) == ("dark", "soft")


def test_disabled_palette_falls_back_to_default():
    look.update(
        palettes=["lime", "olive"],
        default_palette="olive",
        default_mode="system",
        default_radius="normal",
    )
    assert look.resolve_look(palette="steel").palette == "olive"
    assert look.resolve_look(palette="lime").palette == "lime"


def test_storefront_renders_choice_from_cookies(client):
    client.cookies["palette"] = "custom"
    client.cookies["accent"] = "navy"
    client.cookies["radius"] = "sharp"
    client.cookies["text_size"] = "l"
    html = client.get(reverse("web:home")).content.decode()
    attrs = 'data-palette="custom" data-accent="navy" data-radius="sharp" data-text="l"'
    assert f'<html lang="ru" {attrs}>' in html
    # Строка состояния — фон палитры, а не «Лайм-тек».
    assert look.PALETTES["custom"]["bg"]["light"] in html


def test_storefront_ignores_injected_values(client):
    client.cookies["palette"] = '"><script>alert(1)</script>'
    client.cookies["radius"] = "x"
    html = client.get(reverse("web:home")).content.decode()
    assert '<html lang="ru">' in html and "alert(1)" not in html


def test_shop_default_mode_and_palette_for_new_visitor(client):
    look.update(
        palettes=["lime", "steel"],
        default_palette="steel",
        default_mode="dark",
        default_radius="soft",
    )
    html = client.get(reverse("web:home")).content.decode()
    assert '<html lang="ru" data-theme="dark" data-palette="steel" data-radius="soft">' in html
    client.cookies["theme"] = "system"
    assert (
        '<html lang="ru" data-palette="steel" data-radius="soft">'
        in client.get("/").content.decode()
    )


def test_theme_form_saves_look_without_javascript(client):
    response = client.post(
        reverse("web:theme"),
        {"theme": "light", "palette": "olive", "radius": "soft", "text": "m", "accent": "bad"},
    )
    assert response.cookies["palette"].value == "olive"
    assert response.cookies["radius"].value == "soft"
    assert response.cookies["text_size"].value == "m"
    assert "accent" not in response.cookies


def test_profile_shows_only_enabled_palettes(client):
    look.update(
        palettes=["lime", "steel"],
        default_palette="lime",
        default_mode="system",
        default_radius="normal",
    )
    html = client.get(reverse("web:profile_look")).content.decode()
    assert 'name="palette" value="steel"' in html
    assert 'name="palette" value="olive"' not in html
    assert 'name="accent"' not in html  # «Своя» выключена


def test_public_and_admin_api(admin_api):
    public = APIClient().get("/api/v1/content/theme/").json()
    assert [p["key"] for p in public["palettes"]] == list(look.PALETTES)
    assert public["default_palette"] == "lime" and len(public["accents"]) == 14

    body = {
        "palettes": ["lime", "olive"],
        "default_palette": "olive",
        "default_mode": "light",
        "default_radius": "sharp",
    }
    saved = admin_api.put(ADMIN, body, format="json")
    assert saved.status_code == 200, saved.content
    assert saved.json()["enabled"] == ["lime", "olive"]
    assert saved.json()["nav_style"] == "solid"  # не передан — прежний
    assert len(saved.json()["palettes"]) == len(look.PALETTES)  # панели — все палитры

    public = APIClient().get("/api/v1/content/theme/").json()
    assert [p["key"] for p in public["palettes"]] == ["lime", "olive"]
    assert public["default_mode"] == "light"

    bad = admin_api.put(ADMIN, {**body, "default_palette": "steel"}, format="json")
    assert bad.status_code == 400


def test_nav_style_saved_and_rendered(admin_api, client):
    body = {
        "palettes": list(look.PALETTES),
        "default_palette": "lime",
        "default_mode": "system",
        "default_radius": "normal",
        "nav_style": "floating",
    }
    saved = admin_api.put(ADMIN, body, format="json")
    assert saved.status_code == 200, saved.content
    assert saved.json()["nav_style"] == "floating"
    assert APIClient().get("/api/v1/content/theme/").json()["nav_style"] == "floating"
    assert '<html lang="ru" data-nav="floating">' in client.get("/").content.decode()

    assert admin_api.put(ADMIN, {**body, "nav_style": "side"}, format="json").status_code == 400
    look.update(**{**body, "nav_style": "solid"})
    assert "data-nav" not in client.get("/").content.decode()


def test_graphite_palette_removed():
    assert "graphite" not in look.PALETTES
    assert look.resolve_look(palette="graphite").palette == "lime"


def test_admin_api_rejects_customer(db):
    customer = User.objects.create_user(email="c@example.com", password="x-Pass-12345")
    client = APIClient()
    client.force_login(customer)
    assert client.get(ADMIN).status_code == 403


def test_default_text_size_for_new_visitor(admin_api, client):
    body = {
        "palettes": list(look.PALETTES),
        "default_palette": "lime",
        "default_mode": "system",
        "default_radius": "normal",
        "default_text": "l",
    }
    saved = admin_api.put(ADMIN, body, format="json")
    assert saved.status_code == 200, saved.content
    assert saved.json()["default_text"] == "l"
    assert '<html lang="ru" data-text="l">' in client.get("/").content.decode()
    # Выбор покупателя важнее: «Обычный» — без атрибута.
    client.cookies["text_size"] = "s"
    assert '<html lang="ru">' in client.get("/").content.decode()
    assert admin_api.put(ADMIN, {**body, "default_text": "xl"}, format="json").status_code == 400


def test_admin_save_resets_own_look_cookies(admin_api):
    admin_api.cookies["palette"] = "olive"
    admin_api.cookies["theme"] = "dark"
    body = {
        "palettes": list(look.PALETTES),
        "default_palette": "steel",
        "default_mode": "light",
        "default_radius": "soft",
    }
    response = admin_api.put(ADMIN, body, format="json")
    assert response.status_code == 200
    for name in look.VISITOR_COOKIES:
        assert response.cookies[name].value == "" and response.cookies[name]["max-age"] == 0


def test_visitor_cookie_names_match_storefront():
    from web import theme

    assert set(look.VISITOR_COOKIES) == {theme.COOKIE, *theme.LOOK_COOKIES.values()}
