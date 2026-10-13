import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    # Счётчики throttling живут в кэше: тесты не должны влиять друг на друга.
    cache.clear()
    yield
    cache.clear()
