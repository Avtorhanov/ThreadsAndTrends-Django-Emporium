from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from accounts import services

from .conftest import PASSWORD

URL = "/api/v1/auth/me/avatar/"


def photo(size=(640, 480), image_format="JPEG", name="me.jpg") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "blue").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def test_set_avatar_makes_square_webp(customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        user = services.set_avatar(customer, photo())
    assert user.avatar.name.startswith("avatars/") and user.avatar.name.endswith(".webp")
    with user.avatar.open("rb") as fh, Image.open(fh) as img:
        assert img.format == "WEBP" and img.size == (320, 320)


def test_replace_and_remove_delete_old_files(customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        first = services.set_avatar(customer, photo()).avatar.name
        second = services.set_avatar(customer, photo((300, 900))).avatar.name
    storage = customer.avatar.storage
    assert first != second
    assert not storage.exists(first) and storage.exists(second)
    with django_capture_on_commit_callbacks(execute=True):
        user = services.remove_avatar(customer)
    assert not user.avatar and not storage.exists(second)


def test_not_an_image_is_rejected(customer):
    fake = SimpleUploadedFile("me.jpg", b"not an image", content_type="image/jpeg")
    with pytest.raises(ValidationError) as exc:
        services.set_avatar(customer, fake)
    assert "avatar" in exc.value.message_dict
    customer.refresh_from_db()
    assert not customer.avatar


def test_account_deletion_removes_avatar(customer, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        name = services.set_avatar(customer, photo()).avatar.name
    storage = customer.avatar.storage
    customer.refresh_from_db()
    with django_capture_on_commit_callbacks(execute=True):
        services.delete_own_account(customer, password=PASSWORD)
    customer.refresh_from_db()
    assert not customer.avatar and not storage.exists(name)


def test_avatar_api(auth_client, api_client, django_capture_on_commit_callbacks):
    assert api_client.put(URL, {"avatar": photo()}, format="multipart").status_code == 401
    assert auth_client.get("/api/v1/auth/me/").json()["avatar_url"] is None
    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.put(URL, {"avatar": photo()}, format="multipart")
    assert response.status_code == 200, response.content
    assert response.json()["avatar_url"].startswith("http://testserver/")
    bad = auth_client.put(URL, {"avatar": SimpleUploadedFile("x.png", b"oops")}, format="multipart")
    assert bad.status_code == 400 and "avatar" in bad.json()
    with django_capture_on_commit_callbacks(execute=True):
        response = auth_client.delete(URL)
    assert response.status_code == 200 and response.json()["avatar_url"] is None
