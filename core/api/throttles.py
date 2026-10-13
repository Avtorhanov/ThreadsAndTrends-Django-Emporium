from rest_framework.throttling import SimpleRateThrottle


class IPRateThrottle(SimpleRateThrottle):
    """Лимит по IP клиента. IP определяется с учётом REST_FRAMEWORK["NUM_PROXIES"]:
    при 0 заголовок X-Forwarded-For игнорируется и подделать его нельзя."""

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
