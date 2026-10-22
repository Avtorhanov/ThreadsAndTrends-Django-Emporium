import pytest
from django.test import Client
from django.urls import reverse

from store.models import CartItem
from store.services import cart as cart_service

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


def variant(product, size=None):
    variants = product.variants.all()
    return variants.get(size=size) if size is not None else variants.first()


def add(client, product, size=None, quantity=1, **extra):
    return client.post(
        reverse("web:cart_add"),
        {"variant": variant(product, size).pk, "quantity": quantity, "next": "/back/"},
        **extra,
    )


def test_guest_cart_lives_in_session(client, shop):
    response = add(client, shop["shirt"], "M", 2)
    assert response.status_code == 302 and response["Location"] == "/back/"
    assert client.session["cart"] == [[variant(shop["shirt"], "M").pk, 2, 1_990_00]]
    assert not CartItem.objects.exists()
    html = client.get(reverse("web:cart")).content.decode()
    assert "Футболка белая" in html and "Размер M" in html
    assert "3 980" in html  # 2 × 1 990 ₽


def test_cart_page_works_without_session(client, db):
    response = client.get(reverse("web:cart"))
    assert response.status_code == 200
    assert "Корзина пуста" in response.content.decode()
    assert "sessionid" not in response.cookies  # чтение корзину не создаёт


def test_guest_quantity_limits_and_errors(client, shop):
    add(client, shop["shirt"], "M", 5)  # остаток 5
    response = add(client, shop["shirt"], "M", 1, follow=True)
    assert "Можно добавить не больше 5 шт." in response.content.decode()
    response = add(client, shop["sold_out"], follow=True)
    assert "Товара нет в наличии." in response.content.decode()


def test_htmx_add_returns_fragment_with_badges(client, shop):
    response = add(client, shop["cap"], **HTMX)
    html = response.content.decode()
    assert response.status_code == 200
    assert "data-added" in html
    assert 'id="cart-badge-top" hx-swap-oob="true">1</span>' in html
    assert 'id="cart-badge-tab" hx-swap-oob="true">1</span>' in html


def test_htmx_add_shows_error_inline(client, shop):
    response = client.post(reverse("web:cart_add"), {}, **HTMX)
    assert "Выберите размер." in response.content.decode()


def test_guest_change_and_remove_line(client, shop):
    add(client, shop["shirt"], "S")
    line_url = reverse("web:cart_line", args=[variant(shop["shirt"], "S").pk])
    response = client.post(line_url, {"quantity": 3}, **HTMX)
    assert response.status_code == 200
    assert client.session["cart"][0][1] == 3
    assert 'id="cart"' in response.content.decode()
    client.post(line_url, {"quantity": 0})
    assert "cart" not in client.session
    # Повторное удаление (вторая вкладка) не ошибка.
    assert client.post(line_url, {"quantity": 0}).status_code == 302


def test_customer_cart_is_in_database(customer_client, customer, shop):
    add(customer_client, shop["cap"], quantity=2)
    item = CartItem.objects.get(cart__owner=customer)
    assert item.quantity == 2
    line_url = reverse("web:cart_line", args=[item.variant_id])
    customer_client.post(line_url, {"quantity": 1})
    item.refresh_from_db()
    assert item.quantity == 1
    customer_client.post(line_url, {"quantity": 0})
    assert not CartItem.objects.exists()


def test_customer_cannot_touch_foreign_line(customer_client, other_customer, shop):
    cart_service.add(other_customer, variant(shop["cap"]).pk, 1)
    line_url = reverse("web:cart_line", args=[variant(shop["cap"]).pk])
    customer_client.post(line_url, {"quantity": 0})
    assert CartItem.objects.filter(cart__owner=other_customer).count() == 1


def test_guest_cart_is_merged_on_login(client, customer, shop):
    cart_service.add(customer, variant(shop["cap"]).pk, 1)
    add(client, shop["cap"], quantity=2)
    add(client, shop["shirt"], "S")
    response = client.post(
        reverse("web:login"), {"email": "Customer@Example.com", "password": PASSWORD}
    )
    assert response.status_code == 302
    assert "cart" not in client.session
    quantities = dict(
        CartItem.objects.filter(cart__owner=customer).values_list("variant_id", "quantity")
    )
    assert quantities == {variant(shop["cap"]).pk: 3, variant(shop["shirt"], "S").pk: 1}


def test_price_change_warning_and_ack(client, shop):
    add(client, shop["cap"])
    shop["cap"].price_kopecks = 1_290_00
    shop["cap"].save()
    assert "Цены некоторых товаров изменились" in client.get(reverse("web:cart")).content.decode()
    client.post(reverse("web:cart_ack_prices"))
    assert "Цены некоторых" not in client.get(reverse("web:cart")).content.decode()


def test_unavailable_line_blocks_checkout_button(client, shop):
    add(client, shop["cap"])
    shop["cap"].is_active = False
    shop["cap"].save()
    html = client.get(reverse("web:cart")).content.decode()
    assert "Недоступен" in html
    assert reverse("web:checkout") not in html


def test_corrupted_session_cart_does_not_break_page(client, shop):
    session = client.session
    session["cart"] = [["x", 1, None], [variant(shop["cap"]).pk, 1, None], "junk"]
    session.save()
    assert "Кепка" in client.get(reverse("web:cart")).content.decode()


def test_cart_forms_require_csrf(shop):
    client = Client(enforce_csrf_checks=True)
    response = client.post(reverse("web:cart_add"), {"variant": variant(shop["cap"]).pk})
    assert response.status_code == 403
