"""Настройки сборки визуального превью (GitHub Pages). Только для deploy/preview/build.py.

Основа — тестовые настройки: детерминированные условия заказа (самовывоз, онлайн-оплата),
кэш в памяти, фоновые задачи сразу. Сверху — файлы на диске (фото и превью), адреса статики
и медиа под путём Pages, демо-контакты и реквизиты для подвала и «Контактов».
"""

import os

from core.env import database_from_env
from myshop.settings.test import *  # noqa: F403
from myshop.settings.test import BASE_DIR, TEMPLATES

# Путь сайта на Pages: /<репозиторий> (без завершающего слэша; пусто — корень домена).
PREVIEW_BASE = os.environ.get("PREVIEW_BASE", "").rstrip("/")

DATABASES = {"default": database_from_env()}
ALLOWED_HOSTS = ["*"]
DEBUG = False

STATIC_URL = f"{PREVIEW_BASE}/static/"
MEDIA_URL = f"{PREVIEW_BASE}/media/"
MEDIA_ROOT = os.environ.get("PREVIEW_MEDIA_ROOT", str(BASE_DIR / ".preview-media"))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Шаблон страницы «Все комнаты».
TEMPLATES[0]["DIRS"] = [BASE_DIR / "deploy/preview/templates"]

SITE_URL = os.environ.get("PREVIEW_SITE_URL", "")
ANDROID_APK_URL = "https://example.invalid/didi-shop.apk"

SELLER_NAME = "ИП Пример Продавец (демо)"
SELLER_INN = "000000000000"
SELLER_OGRN = "000000000000000"
SELLER_ADDRESS = "Москва, ул. Примерная, 1"
SELLER_EMAIL = "hello@example.ru"
SELLER_PHONE = "+7 900 123-45-67"
CONTACT_WHATSAPP = "+7 900 123-45-67"
CONTACT_TELEGRAM = "@didishop_demo"
CONTACT_VK = "didishop_demo"
