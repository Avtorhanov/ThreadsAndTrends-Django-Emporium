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
ORDERS_UNPAID_TIMEOUT_MINUTES = 30
# Ключи тестового окружения: провайдер в тестах подменяется фейком (payments/tests/fake.py).
YOOKASSA_SHOP_ID = "test-shop"
YOOKASSA_SECRET_KEY = "test-secret"
PAYMENTS_RETURN_URL_PREFIXES = ["didishop://", "exp://"]
PAYMENTS_RECEIPTS_ENABLED = True
PAYMENTS_TAX_SYSTEM_CODE = 2
PAYMENTS_VAT_CODE = 1
PAYMENTS_RECEIPT_PAYMENT_MODE = "full_payment"
# Случайный вызов настоящего API в тестах падает сразу (порт discard), а не уходит в сеть.
YOOKASSA_API_URL = "http://127.0.0.1:9/v3"
YOOKASSA_TIMEOUT = 1
