"""Смена email: пароль + код на новый адрес, уведомление на прежний. Приложение (JWT),
панель (сессия + CSRF) и сайт работают через одни и те же accounts.services."""

import re
from datetime import timedelta

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import services
from accounts.models import EmailChangeCode

from .conftest import PASSWORD, login

pytestmark = pytest.mark.django_db

APP_REQUEST = "/api/v1/auth/email/change/"
APP_CONFIRM = "/api/v1/auth/email/change/confirm/"
PANEL_REQUEST = "/api/v1/admin/auth/email/change/"
PANEL_CONFIRM = "/api/v1/admin/auth/email/change/confirm/"
NEW = "new.address@example.com"


def code_from_mail():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


@pytest.fixture
def app_client(customer):
    client = APIClient()
    access = login(client, customer.email).json()["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def test_full_flow_via_app(app_client, customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = app_client.post(
            APP_REQUEST, {"new_email": " New.Address@Example.com ", "password": PASSWORD}
        )
    assert response.status_code == 202, response.content
    assert response.json()["new_email"] == NEW
    assert mail.outbox[-1].to == [NEW]
    code = code_from_mail()
    # В БД — только HMAC; email ещё прежний.
    assert not EmailChangeCode.objects.filter(code_hash=code).exists()
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"

    with django_capture_on_commit_callbacks(execute=True):
        response = app_client.post(APP_CONFIRM, {"code": code})
    assert response.status_code == 200, response.content
    assert response.json()["email"] == NEW
    customer.refresh_from_db()
    assert customer.email == NEW
    # Уведомление — на прежний адрес, новый в нём замаскирован.
    notice = mail.outbox[-1]
    assert notice.to == ["customer@example.com"]
    assert NEW not in notice.body and "n***s@example.com" in notice.body
    # Вход — по новому адресу, текущий токен работает.
    assert login(APIClient(), NEW).status_code == 200
    assert login(APIClient(), "customer@example.com").status_code == 401
    assert app_client.get("/api/v1/auth/me/").status_code == 200
    # Код одноразовый.
    assert app_client.post(APP_CONFIRM, {"code": code}).status_code == 400


def test_request_checks_password_and_address(customer, other_customer):
    cases = [
        ({"new_email": NEW, "password": "wrong"}, "password"),
        ({"new_email": "not-an-email", "password": PASSWORD}, "new_email"),
        ({"new_email": "CUSTOMER@example.com", "password": PASSWORD}, "new_email"),
        ({"new_email": other_customer.email, "password": PASSWORD}, "new_email"),
    ]
    for data, field in cases:
        with pytest.raises(ValidationError) as exc:
            services.request_email_change(customer, **data)
        assert field in exc.value.error_dict
    assert not EmailChangeCode.objects.exists()


def test_resend_cooldown_and_only_last_code_works(customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)
    first = code_from_mail()
    with pytest.raises(ValidationError):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)

    EmailChangeCode.objects.update(created_at=timezone.now() - timedelta(minutes=2))
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email="third@example.com", password=PASSWORD)
    second = code_from_mail()
    if first != second:
        with pytest.raises(ValidationError):
            services.confirm_email_change(customer, code=first)
    assert services.confirm_email_change(customer, code=second).email == "third@example.com"


def test_attempts_limit_and_expiry(customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)
    code = code_from_mail()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(ValidationError):
            services.confirm_email_change(customer, code=wrong)
    # После 5 неудач и верный код не принимается.
    with pytest.raises(ValidationError):
        services.confirm_email_change(customer, code=code)

    EmailChangeCode.objects.all().delete()
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)
    code = code_from_mail()
    EmailChangeCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(ValidationError):
        services.confirm_email_change(customer, code=code)
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"


def test_address_taken_while_waiting_for_code(
    customer, django_user_model, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)
    code = code_from_mail()
    django_user_model.objects.create_user(email=NEW, password=PASSWORD)
    with pytest.raises(ValidationError) as exc:
        services.confirm_email_change(customer, code=code)
    assert "занят" in str(exc.value)
    customer.refresh_from_db()
    assert customer.email == "customer@example.com"


def test_code_is_bound_to_its_user(customer, other_customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        services.request_email_change(customer, new_email=NEW, password=PASSWORD)
    code = code_from_mail()
    with pytest.raises(ValidationError):
        services.confirm_email_change(other_customer, code=code)
    other_customer.refresh_from_db()
    assert other_customer.email == "other@example.com"


def test_app_endpoints_require_auth():
    client = APIClient()
    assert client.post(APP_REQUEST, {"new_email": NEW, "password": PASSWORD}).status_code == 401
    assert client.post(APP_CONFIRM, {"code": "123456"}).status_code == 401


# --- Панель ---


def test_panel_flow_for_staff(staff, django_capture_on_commit_callbacks):
    client = APIClient()
    client.force_login(staff)
    assert client.get(PANEL_REQUEST).status_code == 204
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(PANEL_REQUEST, {"new_email": NEW, "password": PASSWORD})
    assert response.status_code == 202, response.content
    assert client.get(PANEL_REQUEST).json()["new_email"] == NEW

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(PANEL_CONFIRM, {"code": code_from_mail()})
    assert response.status_code == 200, response.content
    assert response.json()["email"] == NEW
    # Сессия панели осталась.
    assert client.get("/api/v1/admin/auth/me/").json()["email"] == NEW


def test_panel_cancel_and_profile_update(staff):
    client = APIClient()
    client.force_login(staff)
    services.request_email_change(staff, new_email=NEW, password=PASSWORD)
    assert client.delete(PANEL_REQUEST).status_code == 204
    assert client.get(PANEL_REQUEST).status_code == 204

    response = client.patch(
        "/api/v1/admin/auth/me/", {"first_name": " Анна ", "last_name": "Ли"}, format="json"
    )
    assert response.status_code == 200
    staff.refresh_from_db()
    assert (staff.first_name, staff.last_name) == ("Анна", "Ли")


def test_panel_endpoints_require_staff_session_and_csrf(customer, staff):
    body = {"new_email": NEW, "password": PASSWORD}
    assert APIClient().post(PANEL_REQUEST, body).status_code == 401
    shopper = APIClient()
    shopper.force_login(customer)
    assert shopper.post(PANEL_REQUEST, body).status_code == 403
    assert shopper.patch("/api/v1/admin/auth/me/", {"first_name": "X"}).status_code == 403
    # JWT приложения в панель не пускает.
    jwt = APIClient()
    jwt.credentials(HTTP_AUTHORIZATION=f"Bearer {login(APIClient(), staff.email).json()['access']}")
    assert jwt.post(PANEL_REQUEST, body).status_code == 401
    no_csrf = APIClient(enforce_csrf_checks=True)
    no_csrf.force_login(staff)
    assert no_csrf.post(PANEL_REQUEST, body).status_code == 403
    assert no_csrf.patch("/api/v1/admin/auth/me/", {"first_name": "X"}).status_code == 403
    assert not EmailChangeCode.objects.exists()


# --- Сайт ---


def test_site_flow(client, customer, django_capture_on_commit_callbacks):
    client.force_login(customer)
    page = client.get(reverse("web:profile_data")).content.decode()
    assert "логин аккаунта" not in page
    assert 'id="password"' in page and 'id="email"' in page

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("web:email_change"), {"new_email": NEW, "password": PASSWORD}
        )
    assert response.status_code == 302
    assert "Подтвердить email" in client.get(reverse("web:profile_data")).content.decode()

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("web:email_change_confirm"), {"code": code_from_mail()})
    assert response.status_code == 302
    customer.refresh_from_db()
    assert customer.email == NEW
    # Сессия сайта осталась.
    assert client.get(reverse("web:profile")).context["user"].is_authenticated


def test_site_errors_and_old_password_page(client, customer):
    client.force_login(customer)
    response = client.post(reverse("web:email_change"), {"new_email": NEW, "password": "nope"})
    assert response.status_code == 200
    assert "Неверный пароль." in response.content.decode()
    # Отдельной страницы смены пароля нет — ведёт в «Личные данные».
    response = client.get(reverse("web:password_change"))
    assert response.status_code == 302
    assert response["Location"] == reverse("web:profile_data") + "#password"
