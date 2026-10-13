from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db):
    return User.objects.create_user(email="customer@example.com", password=PASSWORD)


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)


@pytest.fixture
def admin_client(staff):
    client = APIClient()
    client.force_login(staff)
    return client


def image_file(image_format="PNG", name="photo.png", size=(8, 8)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "red").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/octet-stream")
