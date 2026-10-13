import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from orders.models import OrderStatus, PaymentMethod
from orders.tests.factories import make_order
from store.tests.factories import make_product

from .fake import FakeProvider

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture
def fake_provider(monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr("payments.providers.get_provider", lambda: fake)
    return fake


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
def online_order(customer):
    """Онлайн-заказ «Ожидает оплаты»: 2 × 1 500 ₽ = 3 000 ₽, остатки уже списаны."""
    product = make_product(name="Футболка", price_kopecks=1_500_00, stock=5, sizes=("M",))
    return make_order(
        customer,
        product,
        status=OrderStatus.AWAITING_PAYMENT,
        payment_method=PaymentMethod.ONLINE,
        quantity=2,
    )
