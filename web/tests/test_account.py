import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.urls import reverse
from rest_framework.throttling import SimpleRateThrottle

from orders.models import OrderStatus
from orders.tests.factories import make_order

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

User = get_user_model()


def login(client, email="customer@example.com", password=PASSWORD, **extra):
    return client.post(reverse("web:login"), {"email": email, "password": password, **extra})


def test_login_and_logout(client, customer):
    response = login(client, next="/cart/")
    assert response.status_code == 302 and response["Location"] == "/cart/"
    assert client.get(reverse("web:profile")).context["user"] == customer
    client.post(reverse("web:logout"))
    assert not client.get(reverse("web:profile")).context["user"].is_authenticated


def test_login_ignores_external_next(client, customer):
    response = login(client, next="https://evil.example/")
    assert response["Location"] == reverse("web:profile")


def test_wrong_password(client, customer):
    response = login(client, password="nope")
    assert response.status_code == 200
    assert "Неверный email или пароль." in response.content.decode()


def test_staff_cannot_login_to_storefront(client, staff):
    response = login(client, email="staff@example.com")
    html = response.content.decode()
    assert "войдите в панель управления" in html and 'href="/panel/"' in html
    assert "_auth_user_id" not in client.session


def test_login_is_rate_limited(client, customer, monkeypatch):
    rates = {**SimpleRateThrottle.THROTTLE_RATES, "auth_login": "2/min"}
    monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", rates)
    login(client, password="bad")
    login(client, password="bad")
    response = login(client)  # верный пароль, но лимит исчерпан
    assert "Слишком много попыток" in response.content.decode()
    assert "_auth_user_id" not in client.session


def test_register_requires_consent_and_logs_in(client, db):
    data = {"email": "new@example.com", "password": PASSWORD, "first_name": "Анна"}
    response = client.post(reverse("web:register"), data)
    assert "Без согласия" in response.content.decode()
    assert not User.objects.filter(email="new@example.com").exists()

    response = client.post(reverse("web:register"), {**data, "consent": "on"})
    assert response.status_code == 302
    user = User.objects.get(email="new@example.com")
    assert user.first_name == "Анна" and not user.is_staff
    assert client.session["_auth_user_id"] == str(user.pk)


def test_register_validates_password_and_duplicates(client, customer):
    response = client.post(
        reverse("web:register"),
        {"email": "x@example.com", "password": "123", "consent": "on"},
    )
    assert "Введённый пароль слишком короткий" in response.content.decode()
    response = client.post(
        reverse("web:register"),
        {"email": "customer@example.com", "password": PASSWORD, "consent": "on"},
    )
    assert "уже зарегистрирован" in response.content.decode()


def test_password_reset_flow(client, customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("web:password_reset"), {"email": "customer@example.com"})
    assert response.status_code == 302
    assert "email=customer%40example.com" in response["Location"]
    code = re.search(r"\b(\d{6})\b", mail.outbox[0].body).group(1)

    new_password = "N3w-Str0ng-Pass!"
    response = client.post(
        reverse("web:password_reset_confirm"),
        {"email": "customer@example.com", "code": code, "new_password": new_password},
    )
    assert response.status_code == 302 and response["Location"] == reverse("web:profile")
    customer.refresh_from_db()
    assert customer.check_password(new_password)
    assert client.session["_auth_user_id"] == str(customer.pk)


def test_password_reset_does_not_reveal_email(client, db):
    response = client.post(reverse("web:password_reset"), {"email": "nobody@example.com"})
    assert response.status_code == 302
    assert not mail.outbox


def test_password_reset_wrong_code(client, customer):
    response = client.post(
        reverse("web:password_reset_confirm"),
        {"email": "customer@example.com", "code": "000000", "new_password": "N3w-Str0ng-Pass!"},
    )
    assert "Неверный или просроченный код." in response.content.decode()


def test_profile_update(customer_client, customer):
    customer_client.post(reverse("web:profile"), {"first_name": " Пётр ", "last_name": "Ив"})
    customer.refresh_from_db()
    assert (customer.first_name, customer.last_name) == ("Пётр", "Ив")


def test_password_change_keeps_this_session_only(customer, client):
    other = Client()
    login(client)
    login(other)
    response = client.post(
        reverse("web:password_change"),
        {"old_password": PASSWORD, "new_password": "N3w-Str0ng-Pass!"},
    )
    assert response.status_code == 302
    assert client.get(reverse("web:profile")).context["user"].is_authenticated
    assert not other.get(reverse("web:profile")).context["user"].is_authenticated


def test_password_change_requires_old_password(customer_client):
    response = customer_client.post(
        reverse("web:password_change"),
        {"old_password": "wrong", "new_password": "N3w-Str0ng-Pass!"},
    )
    assert "Неверный текущий пароль." in response.content.decode()


def test_delete_account(customer_client, customer):
    response = customer_client.post(reverse("web:delete_account"), {"password": PASSWORD})
    assert response.status_code == 302
    customer.refresh_from_db()
    assert customer.is_deleted and not customer.is_active
    assert "_auth_user_id" not in customer_client.session


def test_delete_account_blocked_by_unfinished_order(customer_client, customer):
    make_order(customer, status=OrderStatus.CONFIRMED)
    response = customer_client.post(reverse("web:delete_account"), {"password": PASSWORD})
    assert "незавершённые заказы" in response.content.decode()
    customer.refresh_from_db()
    assert not customer.is_deleted


@pytest.mark.parametrize("name", ["password_change", "delete_account", "orders", "checkout"])
def test_private_pages_redirect_guest_to_login(client, db, name):
    response = client.get(reverse(f"web:{name}"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("web:login") + "?next=")


def test_guest_profile_offers_login(client, db):
    html = client.get(reverse("web:profile")).content.decode()
    assert reverse("web:login") in html and reverse("web:register") in html


def test_login_requires_csrf(customer):
    client = Client(enforce_csrf_checks=True)
    response = login(client)
    assert response.status_code == 403
