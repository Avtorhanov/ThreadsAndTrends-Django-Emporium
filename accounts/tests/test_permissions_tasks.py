from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from accounts import services
from accounts.models import PasswordResetCode
from accounts.tasks import cleanup_auth_records
from core.api.permissions import IsAdmin, IsOwner

User = get_user_model()

pytestmark = pytest.mark.django_db


def request_for(user):
    return SimpleNamespace(user=user)


def test_is_admin(customer, staff):
    permission = IsAdmin()
    assert permission.has_permission(request_for(staff), None)
    assert not permission.has_permission(request_for(customer), None)
    assert not permission.has_permission(request_for(AnonymousUser()), None)
    staff.is_active = False
    assert not permission.has_permission(request_for(staff), None)


def test_is_owner(customer, other_customer):
    permission = IsOwner()
    view = SimpleNamespace(owner_field="owner")
    own = SimpleNamespace(owner_id=customer.pk)
    assert permission.has_object_permission(request_for(customer), view, own)
    assert not permission.has_object_permission(request_for(other_customer), view, own)
    assert not permission.has_object_permission(request_for(AnonymousUser()), view, own)

    self_view = SimpleNamespace(owner_field="self")
    assert permission.has_object_permission(request_for(customer), self_view, customer)
    assert not permission.has_object_permission(request_for(customer), self_view, other_customer)


def test_cleanup_removes_expired_tokens_and_codes(customer):
    services.issue_tokens(customer)
    services.issue_tokens(customer)
    OutstandingToken.objects.filter(pk=OutstandingToken.objects.first().pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )
    now = timezone.now()
    PasswordResetCode.objects.create(
        user=customer, code_hash="x", expires_at=now - timedelta(days=2)
    )
    fresh = PasswordResetCode.objects.create(
        user=customer, code_hash="y", expires_at=now + timedelta(minutes=5)
    )

    cleanup_auth_records.enqueue()

    assert OutstandingToken.objects.count() == 1
    assert list(PasswordResetCode.objects.all()) == [fresh]


def test_cleanup_is_registered_as_periodic_task(settings):
    assert {
        "task": "accounts.tasks.cleanup_auth_records",
        "every": 24 * 60 * 60,
    } in settings.PERIODIC_TASKS


def test_soft_delete_is_idempotent(customer):
    services.soft_delete_user(customer)
    deleted_at = customer.deleted_at
    services.soft_delete_user(customer)
    customer.refresh_from_db()
    assert customer.deleted_at == deleted_at
