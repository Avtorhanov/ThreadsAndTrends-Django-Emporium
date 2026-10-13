import hashlib

from rest_framework.throttling import SimpleRateThrottle

from accounts.models import normalize_email
from core.api.throttles import IPRateThrottle


class EmailRateThrottle(SimpleRateThrottle):
    """Лимит по email из тела запроса: защищает аккаунт от перебора с разных IP."""

    def get_cache_key(self, request, view):
        data = request.data if isinstance(request.data, dict) else {}
        email = normalize_email(str(data.get("email", "")))
        if not email:
            return None
        ident = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginIPThrottle(IPRateThrottle):
    scope = "auth_login"


class LoginEmailThrottle(EmailRateThrottle):
    scope = "auth_login_email"


class RegisterThrottle(IPRateThrottle):
    scope = "auth_register"


class PasswordResetThrottle(IPRateThrottle):
    scope = "password_reset"


class PasswordResetConfirmThrottle(IPRateThrottle):
    scope = "password_reset_confirm"


class PasswordResetConfirmEmailThrottle(EmailRateThrottle):
    scope = "password_reset_confirm_email"


class SensitiveActionThrottle(IPRateThrottle):
    """Действия с проверкой пароля (смена пароля, удаление аккаунта)."""

    scope = "auth_sensitive"
