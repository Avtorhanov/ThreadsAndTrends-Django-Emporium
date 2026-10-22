from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from payments.tests.fake import FakeProvider
from store.tests.factories import make_category, make_product

User = get_user_model()

PASSWORD = "Str0ng-Passw0rd!"


@pytest.fixture
def customer(db):
    return User.objects.create_user(
        email="customer@example.com", password=PASSWORD, first_name="Иван"
    )


@pytest.fixture
def other_customer(db):
    return User.objects.create_user(email="other@example.com", password=PASSWORD)


@pytest.fixture
def staff(db):
    return User.objects.create_user(email="staff@example.com", password=PASSWORD, is_staff=True)


@pytest.fixture
def customer_client(client, customer):
    client.force_login(customer)
    return client


@pytest.fixture
def fake_provider(monkeypatch):
    fake = FakeProvider()
    monkeypatch.setattr("payments.providers.get_provider", lambda: fake)
    return fake


@pytest.fixture
def shop(db):
    """Одежда → Футболки (видимые товары), плюс скрытый, удалённый, без остатка и товар в
    скрытой категории."""
    clothes = make_category("Одежда", slug="odezhda")
    tees = make_category("Футболки", parent=clothes, slug="futbolki")
    hidden_category = make_category("Архив", slug="arhiv", is_active=False)
    shirt = make_product(
        "Футболка белая",
        category=tees,
        slug="futbolka-belaya",
        price_kopecks=1_990_00,
        compare_at_kopecks=2_490_00,
        sizes=("S", "M"),
    )
    cap = make_product("Кепка", category=clothes, slug="kepka", price_kopecks=990_00)
    sold_out = make_product("Худи", category=tees, slug="hudi", stock=0)
    hidden = make_product("Скрытый", category=tees, slug="skrytyy", is_active=False)
    deleted = make_product("Удалённый", category=tees, slug="udalennyy")
    deleted.deleted_at = timezone.now()
    deleted.save(update_fields=["deleted_at"])
    archived = make_product("В архиве", category=hidden_category, slug="v-arhive")
    return {
        "clothes": clothes,
        "tees": tees,
        "hidden_category": hidden_category,
        "shirt": shirt,
        "cap": cap,
        "sold_out": sold_out,
        "hidden": hidden,
        "deleted": deleted,
        "archived": archived,
    }


def image_file(size=(1200, 1500), name="photo.jpg", image_format="JPEG") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, "green").save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")
