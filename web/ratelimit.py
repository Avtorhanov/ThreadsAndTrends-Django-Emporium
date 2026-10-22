"""Лимиты попыток для форм витрины.

Те же области (scope), ставки (REST_FRAMEWORK.DEFAULT_THROTTLE_RATES) и ключи кэша, что у API
приложения: попытки входа через сайт и через приложение считаются вместе, обойти лимит
переключением клиента нельзя. IP определяется так же (с учётом NUM_PROXIES).
"""

import hashlib

from rest_framework.throttling import SimpleRateThrottle

from accounts.models import normalize_email

TOO_MANY = "Слишком много попыток. Подождите немного и попробуйте снова."


class _Limit(SimpleRateThrottle):
    def __init__(self, scope: str, ident: str | None):
        self.scope = scope
        self.ident = ident
        super().__init__()

    def get_cache_key(self, request, view):
        ident = self.ident if self.ident is not None else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


def allow(request, scope: str, *, email: str | None = None, user=None) -> bool:
    """Засчитать попытку. False — лимит исчерпан (попытка не засчитывается).

    Ключ: email (sha256, как у API) → пользователь → IP клиента."""
    if email is not None:
        normalized = normalize_email(email)
        if not normalized:
            return True
        ident = hashlib.sha256(normalized.encode()).hexdigest()
    elif user is not None:
        ident = str(user.pk)
    else:
        ident = None
    return _Limit(scope, ident).allow_request(request, None)
