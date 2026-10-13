from unittest import mock

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_health_ok_without_auth(client):
    response = client.get(reverse("v1:health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": True, "cache": True}}


def test_health_returns_503_when_cache_fails(client):
    with mock.patch("core.api.views.cache.set", side_effect=ConnectionError):
        response = client.get(reverse("v1:health"))
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": True, "cache": False}


def test_openapi_schema_hidden_from_anonymous_in_non_dev(client):
    # test/prod: схема только для администратора
    response = client.get(reverse("v1:schema"))
    assert response.status_code in (401, 403)


def test_openapi_schema_available_to_admin(admin_client):
    response = admin_client.get(reverse("v1:schema"))
    assert response.status_code == 200
    assert b"/api/v1/health/" in response.content
