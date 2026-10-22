"""Регрессия на «мины» из аудита, исправленные в сессии 1."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

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

    response = client.get(reverse("web:home"))

    assert response.status_code == 200
    assert not Cart.objects.filter(owner=user).exists()
