import os

from core.env import env_bool, env_float, env_int, env_str

from .base import *  # noqa: F403

DEBUG = False

# Статика с хэшем содержимого в имени (site.3f2a….css): Caddy отдаёт её с долгим кэшем,
# после обновления браузер сразу получает новые файлы. Манифест строит collectstatic в образе.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
}

# За reverse proxy (Caddy, deploy/Caddyfile) с терминацией TLS. Caddy передаёт реальный IP
# клиента в X-Forwarded-For (входящий заголовок от клиента отбрасывает) — NUM_PROXIES=1.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/$"]
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
# HSTS: год, с поддоменами. Сайт работает только по HTTPS (Caddy выпускает сертификат сам).
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
# Включение в HSTS preload-список браузеров — осознанное решение владельца домена
# (отменяется месяцами), поэтому по умолчанию выключено и предупреждение не нужно.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Почта: пока SMTP не настроен (EMAIL_HOST пуст), письма — в лог воркера
# (`./deploy.sh logs worker`), чтобы коды сброса пароля можно было найти при проверке.
if not os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Мониторинг ошибок (Sentry): включается переменной SENTRY_DSN ---
# Логгер payments пишет ERROR при несовпавшей сумме, отказе в возврате и чужом платеже —
# такие записи уходят в Sentry событиями (LoggingIntegration, уровень ERROR).
SENTRY_DSN = env_str("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env_str("SENTRY_ENVIRONMENT", "production"),
        release=env_str("APP_VERSION", "") or None,
        traces_sample_rate=env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0),
        # Персональные данные покупателей (email, IP, cookies) в Sentry не отправляются.
        send_default_pii=False,
    )
