"""Общие настройки. Окружения: dev, test, prod (myshop.settings.<env>)."""

from pathlib import Path

from dotenv import load_dotenv

from core.env import (
    cache_from_url,
    database_from_env,
    env_bool,
    env_list,
    env_str,
    tasks_from_env,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# .env удобен локально; в контейнерах и на сервере переменные приходят из окружения
# и имеют приоритет (override=False).
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = env_str("SECRET_KEY")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "drf_spectacular",
    "django_tasks",
    "django_tasks_db",
    # local
    "core",
    "store.apps.StoreConfig",
    "accounts",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
                "core.context_processors.header_counters",
            ],
        },
    },
]

WSGI_APPLICATION = "myshop.wsgi.application"
ASGI_APPLICATION = "myshop.asgi.application"

DATABASES = {"default": database_from_env()}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Кэш переключается переменной CACHE_URL без правок кода (см. core.env.cache_from_url).
# По умолчанию — таблица в Postgres: общий для всех воркеров gunicorn, без отдельного сервиса.
CACHES = {"default": cache_from_url(env_str("CACHE_URL", "db://django_cache"))}

# Фоновые задачи: API django.tasks; бэкенд выбирается TASKS_BACKEND.
TASKS = {"default": tasks_from_env()}

# Периодические задачи для `manage.py run_scheduler`:
# {"task": "app.tasks.func", "every": <секунды>}. Заполняются в сессиях 5–6.
PERIODIC_TASKS: list[dict] = []

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-RU"
TIME_ZONE = env_str("TIME_ZONE", "Europe/Moscow")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env_str("MEDIA_ROOT", str(BASE_DIR / "media")))

# --- API для мобильного приложения ---
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    # Схема аутентификации для мобильного клиента выбирается в сессии 2.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DiDi-shop API",
    "DESCRIPTION": "API маркетплейса DiDi-shop для мобильного приложения.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # Схема и Swagger UI — только администратору; в dev открыты всем.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}

LOG_LEVEL = env_str("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.db.backends": {"level": "WARNING"},
    },
}
