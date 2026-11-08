"""Цвета — связанные товары: сервис, витрина, API, снимок в заказе."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from store.models import ProductStatus
from store.services import catalog
from store.services.storefront import color_options

from .factories import make_product

pytestmark = pytest.mark.django_db

PRODUCTS = "/api/v1/admin/catalog/products/"


def link(*pairs):
    return catalog.link_colors([{"id": p.pk, "color_name": name} for p, name in pairs])


def test_link_then_rename_and_extend_keeps_group():
    green, beige, blue = make_product(), make_product(), make_product()
    group, updated = link((green, "Зелёный"), (beige, "Бежевый"))
    assert updated == 2
    assert link((green, "Изумрудный"), (blue, "Синий"))[0] == group
    green.refresh_from_db()
    blue.refresh_from_db()
    assert (green.color_name, blue.color_group) == ("Изумрудный", group)


@pytest.mark.parametrize("second_name", ["зелёный ", ""])
def test_link_rejects_duplicate_or_empty_names(second_name):
    with pytest.raises(ValidationError):
        link((make_product(), "Зелёный"), (make_product(), second_name))


def test_link_rejects_two_groups():
    a, b, c, d = (make_product() for _ in range(4))
    link((a, "1"), (b, "2"))
    link((c, "3"), (d, "4"))
    with pytest.raises(ValidationError):
        link((a, "5"), (c, "6"))


def test_unlink_dissolves_pair_but_keeps_larger_group():
    a, b, c = make_product(), make_product(), make_product()
    link((a, "1"), (b, "2"), (c, "3"))
    a.refresh_from_db()
    catalog.unlink_color(a)
    b.refresh_from_db()
    assert a.color_group is None and a.color_name == "" and b.color_group is not None
    catalog.unlink_color(b)
    c.refresh_from_db()
    assert c.color_group is None and c.color_name == ""


def test_options_only_live_and_at_least_two():
    shown = make_product()
    draft = make_product(is_active=False, is_draft=True)
    link((shown, "Зелёный"), (draft, "Бежевый"))
    shown.refresh_from_db()
    assert color_options(shown) == []
    catalog.bulk_update_products([draft.pk], is_active=True)
    assert len(color_options(shown)) == 2


def test_product_page_and_api_show_switcher(client):
    green, beige = make_product(), make_product(stock=0)
    link((green, "Зелёный"), (beige, "Бежевый"))
    html = client.get(reverse("web:product", args=[green.slug])).content.decode()
    assert "colors__list" in html and "Бежевый, нет в наличии" in html
    data = client.get(f"/api/v1/catalog/products/{green.slug}/").json()
    assert data["color_name"] == "Зелёный"
    assert [(c["slug"], c["in_stock"]) for c in data["colors"]] == [
        (green.slug, True),
        (beige.slug, False),
    ]


def test_product_without_colors_has_no_switcher(client):
    product = make_product()
    assert b"colors__list" not in client.get(reverse("web:product", args=[product.slug])).content


def test_admin_link_and_unlink(admin_client):
    a, b = make_product(), make_product()
    items = [{"id": a.pk, "color_name": "Чёрный"}, {"id": b.pk, "color_name": "Белый"}]
    response = admin_client.post(f"{PRODUCTS}colors/", {"items": items}, format="json")
    assert response.status_code == 200 and response.json()["updated"] == 2
    detail = admin_client.get(f"{PRODUCTS}{a.pk}/").json()
    assert [row["color_name"] for row in detail["color_siblings"]] == ["Белый"]
    response = admin_client.post(f"{PRODUCTS}{a.pk}/colors/unlink/", format="json")
    assert response.status_code == 200 and response.json()["color_group"] is None


def test_cart_shows_color_and_status_hint(client):
    label = ProductStatus.objects.get(name="Под заказ")
    catalog.update_status(label, hint="Поставка 10 дней")
    a, b = make_product(status=label), make_product()
    link((a, "Зелёный"), (b, "Бежевый"))
    variant = a.variants.get()
    client.post(reverse("web:cart_add"), {"variant": variant.pk})
    html = client.get(reverse("web:cart")).content.decode()
    assert "Цвет Зелёный" in html and "Поставка 10 дней" in html
