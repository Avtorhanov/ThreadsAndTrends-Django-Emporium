import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd!"
NEW_PASSWORD = "An0ther-Str0ng-Pass!"


@pytest.fixture
def api_client():
    return APIClient()


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
def superuser(db):
    return User.objects.create_superuser(email="root@example.com", password=PASSWORD)


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")


@pytest.fixture
def tokens(api_client, customer):
    response = login(api_client, customer.email)
    assert response.status_code == 200, response.content
    return response.json()


@pytest.fixture
def auth_client(tokens):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client
