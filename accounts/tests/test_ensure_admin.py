import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_creates_superuser_once(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Owner@Example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Str0ng-Admin-Pass!")
    call_command("ensure_admin")
    admin = User.objects.get(email="owner@example.com")
    assert admin.is_staff and admin.is_superuser
    assert admin.check_password("Str0ng-Admin-Pass!")

    monkeypatch.setenv("ADMIN_PASSWORD", "Another-Str0ng-Pass!")
    call_command("ensure_admin")  # повторный деплой не меняет пароль
    admin.refresh_from_db()
    assert admin.check_password("Str0ng-Admin-Pass!")


def test_rejects_weak_password(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "12345678")
    with pytest.raises(CommandError):
        call_command("ensure_admin")
    assert not User.objects.exists()


def test_does_not_promote_existing_customer(monkeypatch):
    User.objects.create_user(email="owner@example.com", password="x")
    monkeypatch.setenv("ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "Str0ng-Admin-Pass!")
    with pytest.raises(CommandError):
        call_command("ensure_admin")
    assert not User.objects.get(email="owner@example.com").is_staff


def test_skips_without_env(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    call_command("ensure_admin")
    assert not User.objects.exists()
