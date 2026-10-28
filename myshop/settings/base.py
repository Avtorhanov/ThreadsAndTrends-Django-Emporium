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
    "django.contrib.sitemaps",
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
    "payments",
    # Статьи и контакты (вкладка «Контакты» на сайте и в приложении)
    "content",
    # Веб-витрина (Django-шаблоны + htmx): каталог, корзина, оформление, кабинет, SEO.
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "web.middleware.StorefrontHeadersMiddleware",
]

ROOT_URLCONF = "myshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.static",
                "web.context_processors.storefront",
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
    # Сверка зависших платежей и возвратов (потерянный webhook, сбой сети).
    {"task": "payments.tasks.sync_pending", "every": 60},
    # Автоотмена онлайн-заказов, не оплаченных за ORDERS_UNPAID_TIMEOUT_MINUTES.
    {"task": "payments.tasks.cancel_unpaid_orders", "every": 60},
]

# --- Пользователи ---
AUTH_USER_MODEL = "accounts.User"
# Вход на веб-витрине (сессия Django): покупатель — в кабинет, администратор — в панель /panel/.
LOGIN_URL = "web:login"

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
        # Оформление заказа (на пользователя).
        "order_create": env_str("THROTTLE_ORDER_CREATE", "30/hour"),
        # Оплата: получение ссылки и сверка после возврата из браузера (на пользователя).
        "payment_start": env_str("THROTTLE_PAYMENT_START", "30/hour"),
        "payment_refresh": env_str("THROTTLE_PAYMENT_REFRESH", "120/hour"),
    },
}

# --- Корзина ---
# Максимум единиц одного варианта (дополнительно ограничено остатком) и позиций в корзине.
CART_MAX_QUANTITY = env_int("CART_MAX_QUANTITY", 10)
CART_MAX_ITEMS = env_int("CART_MAX_ITEMS", 50)

# --- Панель администратора ---
# «Мало на складе» в сводке: варианты с остатком от 0 до этого числа включительно.
ADMIN_LOW_STOCK_THRESHOLD = env_int("ADMIN_LOW_STOCK_THRESHOLD", 3)

# --- Заказы ---
# Курьерская доставка: стоимость и порог бесплатной доставки (по сумме товаров), копейки.
DELIVERY_COURIER_KOPECKS = env_int("DELIVERY_COURIER_KOPECKS", 500_00)
DELIVERY_FREE_FROM_KOPECKS = env_int("DELIVERY_FREE_FROM_KOPECKS", 10_000_00)
# Адрес пункта самовывоза; пусто — самовывоз не предлагается.
PICKUP_ADDRESS = env_str("PICKUP_ADDRESS", "")
# Онлайн-оплата (ЮKassa) предлагается только при заданных ключах магазина — иначе system check
# payments.E001. По умолчанию выключена: только оплата при получении.
ORDERS_ONLINE_PAYMENT_ENABLED = env_bool("ORDERS_ONLINE_PAYMENT_ENABLED", False)
# Неоплаченный онлайн-заказ отменяется через столько минут, товар возвращается в продажу.
ORDERS_UNPAID_TIMEOUT_MINUTES = env_int("ORDERS_UNPAID_TIMEOUT_MINUTES", 30)

# --- Платежи (ЮKassa) ---
YOOKASSA_SHOP_ID = env_str("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = env_str("YOOKASSA_SECRET_KEY", "")
YOOKASSA_API_URL = env_str("YOOKASSA_API_URL", "https://api.yookassa.ru/v3")
YOOKASSA_TIMEOUT = env_int("YOOKASSA_TIMEOUT", 10)
# Адреса, с которых ЮKassa шлёт уведомления (https://yookassa.ru/developers/using-api/webhooks).
YOOKASSA_WEBHOOK_IPS = env_list(
    "YOOKASSA_WEBHOOK_IPS",
    "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35,"
    "77.75.154.128/25,2a02:5180::/32",
)
# Куда страница оплаты возвращает покупателя: только адреса приложения (в Expo Go — exp://).
PAYMENTS_RETURN_URL_PREFIXES = env_list("PAYMENTS_RETURN_URL_PREFIXES", "didishop://")
PAYMENTS_DEFAULT_RETURN_URL = env_str("PAYMENTS_DEFAULT_RETURN_URL", "didishop://orders/{number}")
# Чеки 54-ФЗ через ЮKassa. Коды: система налогообложения 1 — ОСН, 2 — УСН доходы,
# 3 — УСН доходы минус расходы, 4 — ЕНВД, 5 — ЕСХН, 6 — патент; НДС 1 — без НДС
# (остальные — по справочнику ЮKassa). Значения согласуйте с бухгалтером.
PAYMENTS_RECEIPTS_ENABLED = env_bool("PAYMENTS_RECEIPTS_ENABLED", True)
PAYMENTS_TAX_SYSTEM_CODE = env_int("PAYMENTS_TAX_SYSTEM_CODE", 2)
PAYMENTS_VAT_CODE = env_int("PAYMENTS_VAT_CODE", 1)
PAYMENTS_RECEIPT_PAYMENT_MODE = env_str("PAYMENTS_RECEIPT_PAYMENT_MODE", "full_payment")

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
    "ENUM_NAME_OVERRIDES": {
        "CartMergeNoticeReasonEnum": "store.services.cart.MergeNoticeReason.choices",
        "OrderStatusEnum": "orders.models.OrderStatus.choices",
        "PaymentMethodEnum": "orders.models.PaymentMethod.choices",
        "DeliveryMethodEnum": "orders.models.DeliveryMethod.choices",
        "ChangedByEnum": "orders.models.ChangedBy.choices",
        "PaymentStatusEnum": "payments.models.PaymentStatus.choices",
        "RefundStatusEnum": "payments.models.RefundStatus.choices",
        "RefundReasonEnum": "payments.models.RefundReason.choices",
        "ContactKindEnum": "content.contacts.ContactKind.CHOICES",
        "BlockKindEnum": "content.models.BlockKind.choices",
        "BlockAreaEnum": "content.models.BlockArea.choices",
        "HomeBlockKindEnum": "content.models.HomeBlockKind.choices",
        "CollectionSourceEnum": "content.models.CollectionSource.choices",
        "PaletteKeyEnum": "content.look.PALETTE_CHOICES",
        "PaletteGroupEnum": "content.look.PALETTE_GROUP_CHOICES",
        "ThemeModeEnum": "content.look.MODE_CHOICES",
        "ThemeRadiusEnum": "content.look.RADIUS_CHOICES",
        "ThemeNavEnum": "content.look.NAV_CHOICES",
        "ThemeTextEnum": "content.look.TEXT_CHOICES",
        "HomeLinkKindEnum": "content.home.LINK_KIND_CHOICES",
        "HomeLinkPageEnum": "content.home.LINK_PAGE_CHOICES",
        "StaffLevelEnum": "accounts.staff.LEVEL_CHOICES",
    },
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

# --- Веб-витрина ---
# Основной адрес сайта (https://домен) для canonical, sitemap и Open Graph. Пусто — адрес из
# запроса. В продакшене задаёт compose.prod.yml из DOMAIN: прежние адреса (EXTRA_DOMAINS)
# продолжают работать, но поисковики видят один.
SITE_URL = env_str("SITE_URL", "").rstrip("/")
# Ссылка «Скачать для Android» в баннере на телефонах (пусто — Android-баннер не показывается).
ANDROID_APK_URL = env_str("ANDROID_APK_URL", "")
# Товаров на странице каталога и поиска.
WEB_PAGE_SIZE = env_int("WEB_PAGE_SIZE", 24)
# Сколько секунд хранится готовая сетка товаров (сбрасывается при изменении каталога).
WEB_CATALOG_CACHE_SECONDS = env_int("WEB_CATALOG_CACHE_SECONDS", 300)
# Реквизиты продавца: подвал сайта и юридические страницы (оферта, политика ПДн, доставка).
# Обязательны до подключения ЮKassa; тексты страниц — заготовки, их проверяет юрист.
SELLER_NAME = env_str("SELLER_NAME", "")
SELLER_INN = env_str("SELLER_INN", "")
SELLER_OGRN = env_str("SELLER_OGRN", "")
SELLER_ADDRESS = env_str("SELLER_ADDRESS", "")
SELLER_EMAIL = env_str("SELLER_EMAIL", "")
SELLER_PHONE = env_str("SELLER_PHONE", "")
# Вкладка «Контакты» (сайт и приложение): пусто — канал не показывается. Подписи — свои
# у каждого канала (пусто — подпись по умолчанию). Телефон и email — SELLER_PHONE/SELLER_EMAIL.
CONTACT_WHATSAPP = env_str("CONTACT_WHATSAPP", "")  # номер: +7 900 123-45-67
CONTACT_WHATSAPP_NOTE = env_str("CONTACT_WHATSAPP_NOTE", "")
CONTACT_TELEGRAM = env_str("CONTACT_TELEGRAM", "")  # @имя или https://t.me/имя
CONTACT_TELEGRAM_NOTE = env_str("CONTACT_TELEGRAM_NOTE", "")
CONTACT_VK = env_str("CONTACT_VK", "")  # короткое имя или https://vk.com/имя
CONTACT_VK_NOTE = env_str("CONTACT_VK_NOTE", "")
CONTACT_PHONE_NOTE = env_str("CONTACT_PHONE_NOTE", "")
CONTACT_EMAIL_NOTE = env_str("CONTACT_EMAIL_NOTE", "")
