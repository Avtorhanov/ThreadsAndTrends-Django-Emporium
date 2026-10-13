"""Регрессия на «мины» из аудита, исправленные в сессии 1."""

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import RequestFactory
from django.urls import reverse

from core.context_processors import header_counters
from orders.models import Order
from store.models import Cart, CartItem, Category, Product

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    category = Category.objects.create(name="Одежда")
    return Product.objects.create(name="Футболка", description="d", price=10, category=category)


def test_cart_item_unique_per_cart_and_product(product):
    user = User.objects.create_user(username="u", password="p")
    cart = Cart.objects.create(owner=user)
    CartItem.objects.create(cart=cart, product=product)
    with pytest.raises(IntegrityError):
        CartItem.objects.create(cart=cart, product=product)


def test_pages_do_not_create_cart_for_user(client):
    user = User.objects.create_user(username="u", password="p")
    client.force_login(user)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert not Cart.objects.filter(owner=user).exists()


def test_header_counters_are_lazy(django_assert_num_queries, product):
    user = User.objects.create_user(username="u", password="p")
    cart = Cart.objects.create(owner=user)
    CartItem.objects.create(cart=cart, product=product, quantity=3)
    Order.objects.create(owner=user)

    request = RequestFactory().get("/")
    request.user = user
    request.session = {}

    with django_assert_num_queries(0):
        counters = header_counters(request)["header_counters"]
    with django_assert_num_queries(2):
        assert counters.cart == 1
        assert counters.orders == 1
        # Повторное обращение берётся из cached_property.
        assert counters.cart == 1


def test_header_counters_for_guest_use_session():
    request = RequestFactory().get("/")
    request.user = type("Anon", (), {"is_authenticated": False})()
    request.session = {"cart_products": [1, 2]}

    counters = header_counters(request)["header_counters"]

    assert counters.cart == 2
    assert counters.orders == 0
