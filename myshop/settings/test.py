import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from .base import *  # noqa: E402,F403

# Тесты детерминированы и не зависят от CACHE_URL/TASKS_BACKEND в окружении.
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
TASKS = {"default": {"BACKEND": "django_tasks.backends.immediate.ImmediateBackend"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
LOGGING["root"]["level"] = "WARNING"  # noqa: F405

# Детерминированные условия заказов в тестах (не зависят от окружения).
DELIVERY_COURIER_KOPECKS = 500_00
DELIVERY_FREE_FROM_KOPECKS = 10_000_00
PICKUP_ADDRESS = "Москва, ул. Тестовая, 1"
ORDERS_ONLINE_PAYMENT_ENABLED = True
