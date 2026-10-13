"""Общие настройки. Окружения: dev, test, prod (myshop.settings.<env>)."""

from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from core.env import (
    cache_from_url,
    database_from_env,
    env_bool,
    env_int,
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
    # Django admin — только суперпользователь (резервный вход), см. core.admin
    "core.admin.SuperuserAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
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
# {"task": "app.tasks.func", "every": <секунды>}.
PERIODIC_TASKS: list[dict] = [
    {"task": "accounts.tasks.cleanup_auth_records", "every": 24 * 60 * 60},
]

# --- Пользователи ---
AUTH_USER_MODEL = "accounts.User"
# Шаблонные страницы входа отключены (клиент — мобильное приложение); login_required
# легаси-страниц ведёт на вход в резервную админку.
LOGIN_URL = "admin:login"

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

# --- API: мобильное приложение (JWT) и панель администратора (сессия) ---
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    # JWT первым: без учётных данных ответ 401 с WWW-Authenticate: Bearer.
    # Сессия — для Browsable API в dev; эндпоинты панели принимают только её.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.api.exceptions.exception_handler",
    # Число доверенных прокси перед приложением (nginx = 1). При 0 X-Forwarded-For
    # игнорируется — иначе лимиты обходятся подделкой заголовка.
    "NUM_PROXIES": env_int("NUM_PROXIES", 0),
    # Лимиты хранятся в общем кэше (CACHE_URL) и работают на всех воркерах.
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": env_str("THROTTLE_AUTH_LOGIN", "10/min"),
        "auth_login_email": env_str("THROTTLE_AUTH_LOGIN_EMAIL", "20/hour"),
        "auth_register": env_str("THROTTLE_AUTH_REGISTER", "10/hour"),
        "auth_sensitive": env_str("THROTTLE_AUTH_SENSITIVE", "10/hour"),
        "password_reset": env_str("THROTTLE_PASSWORD_RESET", "5/hour"),
        "password_reset_confirm": env_str("THROTTLE_PASSWORD_RESET_CONFIRM", "10/min"),
        "password_reset_confirm_email": env_str("THROTTLE_PASSWORD_RESET_CONFIRM_EMAIL", "20/hour"),
        # Публичный расчёт гостевой корзины.
        "cart_quote": env_str("THROTTLE_CART_QUOTE", "60/min"),
    },
}

# --- Корзина ---
# Максимум единиц одного варианта (дополнительно ограничено остатком) и позиций в корзине.
CART_MAX_QUANTITY = env_int("CART_MAX_QUANTITY", 10)
CART_MAX_ITEMS = env_int("CART_MAX_ITEMS", 50)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 30)),
    # Refresh одноразовый: при обновлении старый уходит в чёрный список.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # В токен пишется хэш пароля: смена/сброс пароля сразу инвалидирует access-токены.
    "CHECK_REVOKE_TOKEN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": env_str("JWT_SIGNING_KEY", SECRET_KEY),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DiDi-shop API",
    "DESCRIPTION": "API маркетплейса DiDi-shop для мобильного приложения.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # Схема и Swagger UI — только администратору; в dev открыты всем.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SERVE_AUTHENTICATION": ["rest_framework.authentication.SessionAuthentication"],
    "COMPONENT_SPLIT_REQUEST": True,
}

# --- Почта ---
# Отправка — фоновой задачей core.tasks.send_email. Провайдер выбирается переменными EMAIL_*.
EMAIL_BACKEND = env_str("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env_str("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env_str("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env_str("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = env_int("EMAIL_TIMEOUT", 10)
DEFAULT_FROM_EMAIL = env_str("DEFAULT_FROM_EMAIL", "DiDi-shop <noreply@localhost>")

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
