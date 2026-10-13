import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from .conftest import PASSWORD, login

User = get_user_model()

pytestmark = pytest.mark.django_db

CUSTOMERS = "/api/v1/admin/customers/"


@pytest.fixture
def admin_client(staff):
    client = APIClient()
    client.force_login(staff)
    return client


def test_anonymous_gets_401_session_challenge(api_client):
    response = api_client.get(CUSTOMERS)
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Session"


def test_customer_session_is_forbidden(customer):
    client = APIClient()
    client.force_login(customer)
    assert client.get(CUSTOMERS).status_code == 403
    assert client.get("/api/v1/admin/auth/me/").status_code == 403


def test_jwt_is_not_accepted_by_admin_api(api_client, staff):
    access = login(api_client, staff.email).json()["access"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get(CUSTOMERS).status_code == 401


def test_list_contains_only_customers(admin_client, customer, other_customer, staff, superuser):
    response = admin_client.get(CUSTOMERS)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert {row["email"] for row in data["results"]} == {customer.email, other_customer.email}
    assert {row["status"] for row in data["results"]} == {"active"}


def test_list_search_and_status_filter(admin_client, customer, other_customer):
    response = admin_client.get(CUSTOMERS, {"search": "ИВАН"})
    assert [row["id"] for row in response.json()["results"]] == [customer.pk]

    admin_client.post(f"{CUSTOMERS}{other_customer.pk}/block/")
    response = admin_client.get(CUSTOMERS, {"status": "blocked"})
    assert [row["id"] for row in response.json()["results"]] == [other_customer.pk]
    response = admin_client.get(CUSTOMERS, {"status": "active"})
    assert [row["id"] for row in response.json()["results"]] == [customer.pk]


def test_staff_is_not_reachable_through_customers(admin_client, superuser):
    assert admin_client.get(f"{CUSTOMERS}{superuser.pk}/").status_code == 404
    assert admin_client.post(f"{CUSTOMERS}{superuser.pk}/block/").status_code == 404
    assert admin_client.post(f"{CUSTOMERS}{superuser.pk}/delete/").status_code == 404


def test_block_revokes_access_and_unblock_restores(admin_client, api_client, customer):
    tokens = login(api_client, customer.email).json()

    response = admin_client.post(f"{CUSTOMERS}{customer.pk}/block/")
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert login(api_client, customer.email).status_code == 401
    refresh = api_client.post(
        "/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
    )
    assert refresh.status_code == 401

    response = admin_client.post(f"{CUSTOMERS}{customer.pk}/unblock/")
    assert response.json()["status"] == "active"
    assert login(api_client, customer.email).status_code == 200


def test_soft_delete_by_admin(admin_client, customer):
    response = admin_client.post(f"{CUSTOMERS}{customer.pk}/delete/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["email"] == f"deleted-{customer.pk}@deleted.invalid"
    assert User.objects.filter(pk=customer.pk).exists()

    response = admin_client.post(f"{CUSTOMERS}{customer.pk}/unblock/")
    assert response.status_code == 400


# --- Вход в панель (сессия + CSRF) ---


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    assert client.get("/api/v1/admin/auth/csrf/").status_code == 204
    return client, client.cookies["csrftoken"].value


def admin_login(client, token, email, password=PASSWORD):
    return client.post(
        "/api/v1/admin/auth/login/",
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )


def test_admin_login_requires_csrf(staff):
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        "/api/v1/admin/auth/login/", {"email": staff.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 403


def test_admin_login_logout_flow(staff):
    client, token = csrf_client()
    response = admin_login(client, token, staff.email)
    assert response.status_code == 200
    assert response.json()["email"] == staff.email

    # После входа Django ротирует CSRF-токен.
    token = client.cookies["csrftoken"].value
    assert client.get("/api/v1/admin/auth/me/").status_code == 200
    assert client.get(CUSTOMERS).status_code == 200

    response = client.post("/api/v1/admin/auth/logout/", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 204
    assert client.get("/api/v1/admin/auth/me/").status_code == 401


def test_admin_login_rejects_customer(customer):
    client, token = csrf_client()
    response = admin_login(client, token, customer.email)
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль."


def test_admin_post_without_csrf_is_rejected(staff, customer):
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(staff)
    assert client.post(f"{CUSTOMERS}{customer.pk}/block/").status_code == 403
    customer.refresh_from_db()
    assert customer.is_active


# --- Резервная Django admin ---


def test_django_admin_only_for_superuser(staff, superuser):
    client = APIClient()
    client.force_login(staff)
    assert client.get("/admin/").status_code == 302

    client.force_login(superuser)
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/accounts/user/").status_code == 200
