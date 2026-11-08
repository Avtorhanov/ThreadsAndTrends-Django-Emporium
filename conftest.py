import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    # Счётчики throttling живут в кэше: тесты не должны влиять друг на друга.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def cash_on_delivery(db):
    """Включить «Оплату при получении» (по умолчанию выключена — согласование в мессенджере)."""
    from content.models import ShopSettings

    ShopSettings.objects.update_or_create(pk=1, defaults={"cash_on_delivery_enabled": True})
