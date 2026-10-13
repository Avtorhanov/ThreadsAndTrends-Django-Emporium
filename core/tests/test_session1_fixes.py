"""Регрессия на «мины» из аудита, исправленные в сессии 1."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import RequestFactory
from django.urls import reverse

from core.context_processors import header_counters
from orders.models import Order
from store.models import Cart, CartItem
from store.tests.factories import make_product

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    return make_product(name="Футболка", price_kopecks=10_00)


def test_cart_item_unique_per_cart_and_variant(product):
    user = User.objects.create_user(email="u@example.com", password="p")
    cart = Cart.objects.create(owner=user)
    variant = product.variants.get()
    CartItem.objects.create(cart=cart, variant=variant, quantity=1, seen_price_kopecks=10_00)
    with pytest.raises(IntegrityError):
        CartItem.objects.create(cart=cart, variant=variant, quantity=1, seen_price_kopecks=10_00)


def test_pages_do_not_create_cart_for_user(client):
    user = User.objects.create_user(email="u@example.com", password="p")
    client.force_login(user)

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert not Cart.objects.filter(owner=user).exists()


def test_header_counters_are_lazy(django_assert_num_queries):
    user = User.objects.create_user(email="u@example.com", password="p")
    Order.objects.create(owner=user)

    request = RequestFactory().get("/")
    request.user = user
    request.session = {}

    with django_assert_num_queries(0):
        counters = header_counters(request)["header_counters"]
    with django_assert_num_queries(1):
        assert counters.orders == 1
        # Повторное обращение берётся из cached_property.
        assert counters.orders == 1


def test_header_counters_for_guest():
    request = RequestFactory().get("/")
    request.user = type("Anon", (), {"is_authenticated": False})()
    request.session = {}

    assert header_counters(request)["header_counters"].orders == 0
