from core.env import env_bool, env_list, env_str

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK, SPECTACULAR_SETTINGS

DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = ["rest_framework.permissions.AllowAny"]

# Письма (в т.ч. коды сброса пароля) печатаются в лог воркера.
EMAIL_BACKEND = env_str("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# Expo Go возвращается со страницы оплаты по адресу exp://…/--/orders/<номер>.
PAYMENTS_RETURN_URL_PREFIXES = env_list("PAYMENTS_RETURN_URL_PREFIXES", "didishop://,exp://")
