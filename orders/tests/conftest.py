import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from store.services import cart as cart_service
from store.tests.factories import make_product

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture
def customer(db):
    return User.objects.create_user(
        email="customer@example.com", password=PASSWORD, first_name="Иван"
    )


@pytest.fixture
def other_customer(db):
    return User.objects.create_user(email="other@example.com", password=PASSWORD)


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)


@pytest.fixture
def client_api(customer):
    client = APIClient()
    client.force_authenticate(customer)
    return client


@pytest.fixture
def admin_client(staff):
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.fixture
def shirt(db):
    return make_product(name="Футболка", price_kopecks=1_500_00, stock=5, sizes=("S", "M"))


@pytest.fixture
def cap(db):
    return make_product(name="Кепка", price_kopecks=700_00, stock=3)


@pytest.fixture
def filled_cart(customer, shirt, cap):
    """Корзина: 2 × футболка M (3 000 ₽) + 1 × кепка (700 ₽) = 3 700 ₽."""
    cart_service.add(customer, shirt.variants.get(size="M").pk, 2)
    cart_service.add(customer, cap.variants.get().pk, 1)
    return customer
