"""Заголовки безопасности страниц витрины.

CSP задаётся здесь, а не в Caddy: под тем же доменом работают резервная админка и Swagger UI
со своими требованиями к скриптам. Скрипты витрины — только свои файлы из /static/
(никаких inline-скриптов и сторонних доменов), поэтому XSS через внедрённый <script> не исполнится.
form-action не ограничивается: после оформления заказа браузер уходит на страницу оплаты ЮKassa.
"""

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
    ]
)


# API (JSON, Swagger UI) и резервная админка — со своими заголовками.
EXCLUDED_PREFIXES = ("/api/", "/admin/")


class StorefrontHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Страницы витрины, включая 404 по несуществующим адресам.
        if not request.path.startswith(EXCLUDED_PREFIXES):
            response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
            response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
