import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from accounts.models import PasswordResetCode
from orders.models import Order
from store.models import Cart

from .conftest import NEW_PASSWORD, PASSWORD, login

User = get_user_model()

pytestmark = pytest.mark.django_db

ME = "/api/v1/auth/me/"


def bearer(access):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def refresh(client, token):
    return client.post("/api/v1/auth/refresh/", {"refresh": token}, format="json")


# --- Регистрация ---


def test_register_returns_tokens_and_profile(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "New@Example.com", "password": PASSWORD, "first_name": "Анна"},
        format="json",
    )
    assert response.status_code == 201, response.content
    data = response.json()
    assert data["user"]["email"] == "new@example.com"
    assert data["user"]["first_name"] == "Анна"
    assert bearer(data["access"]).get(ME).status_code == 200
    user = User.objects.get(email="new@example.com")
    assert not user.is_staff and user.check_password(PASSWORD)


def test_register_duplicate_email_case_insensitive(api_client, customer):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": customer.email.upper(), "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.parametrize("password", ["123", "password", "12345678901"])
def test_register_validates_password(api_client, password):
    response = api_client.post(
        "/api/v1/auth/register/", {"email": "weak@example.com", "password": password}, format="json"
    )
    assert response.status_code == 400
    assert "password" in response.json()
    assert not User.objects.filter(email="weak@example.com").exists()


def test_register_cannot_create_staff(api_client):
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "x@example.com", "password": PASSWORD, "is_staff": True, "is_superuser": True},
        format="json",
    )
    assert response.status_code == 201
    user = User.objects.get(email="x@example.com")
    assert not user.is_staff and not user.is_superuser


# --- Вход и токены ---


def test_login_success(api_client, customer):
    response = login(api_client, "Customer@Example.com")
    assert response.status_code == 200
    data = response.json()
    assert {"access", "refresh", "user"} <= data.keys()
    customer.refresh_from_db()
    assert customer.last_login is not None


@pytest.mark.parametrize(
    ("email", "password"),
    [("customer@example.com", "wrong-password"), ("nobody@example.com", PASSWORD)],
)
def test_login_invalid_credentials(api_client, customer, email, password):
    response = login(api_client, email, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль."


def test_login_blocked_user(api_client, customer):
    customer.is_active = False
    customer.save()
    assert login(api_client, customer.email).status_code == 401


def test_anonymous_gets_401_with_bearer_challenge(api_client):
    response = api_client.get(ME)
    assert response.status_code == 401
    assert response["WWW-Authenticate"].startswith("Bearer")


def test_garbage_token_is_rejected(api_client):
    assert bearer("not-a-jwt").get(ME).status_code == 401


def test_profile_get_and_patch(auth_client, customer):
    response = auth_client.get(ME)
    assert response.json()["email"] == customer.email

    response = auth_client.patch(
        ME,
        {"first_name": "Пётр", "last_name": "Петров", "email": "hack@example.com"},
        format="json",
    )
    assert response.status_code == 200
    customer.refresh_from_db()
    assert (customer.first_name, customer.last_name) == ("Пётр", "Петров")
    assert customer.email == "customer@example.com"  # email только для чтения


def test_refresh_rotates_and_blacklists_old_token(api_client, tokens):
    response = refresh(api_client, tokens["refresh"])
    assert response.status_code == 200
    new = response.json()
    assert new["refresh"] != tokens["refresh"]
    assert bearer(new["access"]).get(ME).status_code == 200
    # Повторное использование старого refresh — отказ.
    assert refresh(api_client, tokens["refresh"]).status_code == 401


def test_logout_revokes_refresh(api_client, tokens):
    response = api_client.post(
        "/api/v1/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
    )
    assert response.status_code == 204
    assert refresh(api_client, tokens["refresh"]).status_code == 401


def test_logout_with_invalid_token(api_client):
    response = api_client.post("/api/v1/auth/logout/", {"refresh": "garbage"}, format="json")
    assert response.status_code == 400


# --- Смена пароля ---


def test_change_password_requires_old_password(auth_client):
    response = auth_client.post(
        "/api/v1/auth/password/change/",
        {"old_password": "wrong", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    assert "old_password" in response.json()


def test_change_password_validates_new_password(auth_client):
    response = auth_client.post(
        "/api/v1/auth/password/change/",
        {"old_password": PASSWORD, "new_password": "123"},
        format="json",
    )
    assert response.status_code == 400
    assert "new_password" in response.json()


def test_change_password_revokes_other_sessions(api_client, customer, tokens):
    other_device = login(APIClient(), customer.email).json()
    response = bearer(tokens["access"]).post(
        "/api/v1/auth/password/change/",
        {"old_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    new = response.json()

    # Старые refresh всех устройств отозваны, старые access недействительны.
    assert refresh(api_client, tokens["refresh"]).status_code == 401
    assert refresh(api_client, other_device["refresh"]).status_code == 401
    assert bearer(other_device["access"]).get(ME).status_code == 401
    # Текущее устройство продолжает работать с новой парой.
    assert bearer(new["access"]).get(ME).status_code == 200
    assert login(api_client, customer.email, NEW_PASSWORD).status_code == 200


# --- Сброс пароля ---


def request_reset(client, email, capture):
    with capture(execute=True):
        return client.post("/api/v1/auth/password/reset/", {"email": email}, format="json")


def code_from_mail():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def confirm_reset(client, email, code, password=NEW_PASSWORD):
    return client.post(
        "/api/v1/auth/password/reset/confirm/",
        {"email": email, "code": code, "new_password": password},
        format="json",
    )


def test_reset_unknown_email_is_indistinguishable(api_client, django_capture_on_commit_callbacks):
    response = request_reset(api_client, "nobody@example.com", django_capture_on_commit_callbacks)
    assert response.status_code == 202
    assert mail.outbox == []


def test_reset_full_flow(api_client, customer, tokens, django_capture_on_commit_callbacks):
    response = request_reset(api_client, "CUSTOMER@example.com", django_capture_on_commit_callbacks)
    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [customer.email]
    code = code_from_mail()
    # В БД хранится только HMAC кода.
    assert not PasswordResetCode.objects.filter(code_hash=code).exists()

    response = confirm_reset(api_client, customer.email, code)
    assert response.status_code == 200
    assert bearer(response.json()["access"]).get(ME).status_code == 200
    assert refresh(api_client, tokens["refresh"]).status_code == 401
    assert login(api_client, customer.email, NEW_PASSWORD).status_code == 200
    # Код одноразовый.
    assert confirm_reset(api_client, customer.email, code, "Yet-An0ther-Pass!").status_code == 400


def test_reset_resend_cooldown(api_client, customer, django_capture_on_commit_callbacks):
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    assert len(mail.outbox) == 1


def test_reset_new_code_invalidates_previous(
    api_client, customer, django_capture_on_commit_callbacks
):
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    first_code = code_from_mail()
    PasswordResetCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    second_code = code_from_mail()
    if first_code != second_code:
        assert confirm_reset(api_client, customer.email, first_code).status_code == 400
    assert confirm_reset(api_client, customer.email, second_code).status_code == 200


def test_reset_wrong_code_attempts_are_limited(
    api_client, customer, django_capture_on_commit_callbacks
):
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    code = code_from_mail()
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    for _ in range(5):
        assert confirm_reset(api_client, customer.email, wrong).status_code == 400
    assert PasswordResetCode.objects.get().attempts == 5
    # После исчерпания попыток не принимается даже верный код.
    assert confirm_reset(api_client, customer.email, code).status_code == 400


def test_reset_expired_code(api_client, customer, django_capture_on_commit_callbacks):
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    code = code_from_mail()
    PasswordResetCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert confirm_reset(api_client, customer.email, code).status_code == 400


def test_reset_weak_password_does_not_burn_code(
    api_client, customer, django_capture_on_commit_callbacks
):
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    code = code_from_mail()
    response = confirm_reset(api_client, customer.email, code, "123")
    assert response.status_code == 400
    assert "new_password" in response.json()
    assert confirm_reset(api_client, customer.email, code).status_code == 200


def test_reset_not_sent_to_blocked_user(api_client, customer, django_capture_on_commit_callbacks):
    customer.is_active = False
    customer.save()
    request_reset(api_client, customer.email, django_capture_on_commit_callbacks)
    assert mail.outbox == []


# --- Удаление аккаунта ---


def test_delete_account_requires_password(auth_client, customer):
    response = auth_client.post("/api/v1/auth/me/delete/", {"password": "wrong"}, format="json")
    assert response.status_code == 400
    customer.refresh_from_db()
    assert customer.deleted_at is None


def test_delete_account_anonymizes_and_revokes(api_client, customer, tokens):
    Cart.objects.create(owner=customer)
    order = Order.objects.create(owner=customer, full_name="Иван", phone_number="+7900")

    response = bearer(tokens["access"]).post(
        "/api/v1/auth/me/delete/", {"password": PASSWORD}, format="json"
    )
    assert response.status_code == 204

    customer.refresh_from_db()
    assert customer.deleted_at is not None
    assert customer.is_active is False
    assert customer.email == f"deleted-{customer.pk}@deleted.invalid"
    assert customer.first_name == "" and customer.last_name == ""
    assert not customer.has_usable_password()

    assert bearer(tokens["access"]).get(ME).status_code == 401
    assert refresh(api_client, tokens["refresh"]).status_code == 401
    assert login(api_client, "customer@example.com").status_code == 401
    assert not Cart.objects.filter(owner=customer).exists()
    assert Order.objects.filter(pk=order.pk).exists()  # история заказов сохраняется

    # Email освобождается для новой регистрации.
    response = api_client.post(
        "/api/v1/auth/register/",
        {"email": "customer@example.com", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 201


def test_staff_cannot_delete_account_via_app(api_client, staff):
    access = login(api_client, staff.email).json()["access"]
    response = bearer(access).post("/api/v1/auth/me/delete/", {"password": PASSWORD}, format="json")
    assert response.status_code == 403
    staff.refresh_from_db()
    assert staff.deleted_at is None


# --- Rate limit ---


def test_login_is_throttled_by_ip(api_client, customer):
    for _ in range(10):
        assert login(api_client, customer.email, "wrong").status_code == 401
    assert login(api_client, customer.email, PASSWORD).status_code == 429


def test_spoofed_forwarded_for_does_not_bypass_throttle(customer):
    client = APIClient()
    for i in range(10):
        client.post(
            "/api/v1/auth/login/",
            {"email": f"user{i}@example.com", "password": "wrong"},
            format="json",
            HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
        )
    response = client.post(
        "/api/v1/auth/login/",
        {"email": customer.email, "password": PASSWORD},
        format="json",
        HTTP_X_FORWARDED_FOR="10.0.0.99",
    )
    assert response.status_code == 429


def test_login_is_throttled_by_email_across_ips(customer, monkeypatch):
    rates = {**SimpleRateThrottle.THROTTLE_RATES, "auth_login_email": "3/hour"}
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
    for i in range(3):
        response = APIClient(REMOTE_ADDR=f"192.0.2.{i}").post(
            "/api/v1/auth/login/", {"email": customer.email, "password": "x"}, format="json"
        )
        assert response.status_code == 401
    response = APIClient(REMOTE_ADDR="192.0.2.50").post(
        "/api/v1/auth/login/", {"email": customer.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 429
