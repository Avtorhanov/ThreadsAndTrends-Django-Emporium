import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError

from .conftest import PASSWORD

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_email_is_normalized_to_lowercase():
    user = User.objects.create_user(email="  Mixed.Case@Example.COM ", password=PASSWORD)
    assert user.email == "mixed.case@example.com"
    assert user.is_staff is False
    assert user.is_superuser is False


def test_email_is_unique_regardless_of_case():
    User.objects.create_user(email="dup@example.com", password=PASSWORD)
    with pytest.raises(IntegrityError):
        User.objects.create_user(email="DUP@example.com", password=PASSWORD)


def test_authenticate_by_email_case_insensitive():
    user = User.objects.create_user(email="login@example.com", password=PASSWORD)
    assert authenticate(email="LOGIN@Example.com", password=PASSWORD) == user


def test_create_superuser_sets_flags():
    user = User.objects.create_superuser(email="root@example.com", password=PASSWORD)
    assert user.is_staff and user.is_superuser


def test_create_user_requires_email():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password=PASSWORD)


def test_querysets():
    customer = User.objects.create_user(email="c@example.com", password=PASSWORD)
    staff = User.objects.create_user(email="s@example.com", password=PASSWORD, is_staff=True)
    assert list(User.objects.customers()) == [customer]
    assert set(User.objects.alive()) == {customer, staff}
