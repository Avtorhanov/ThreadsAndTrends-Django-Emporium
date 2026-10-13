from functools import cached_property

from orders.models import Order


class HeaderCounters:
    """Счётчики шапки легаси-сайта. Запрос к БД выполняется только при обращении
    из шаблона. Корзина — только в мобильном приложении (сессия 4)."""

    def __init__(self, request):
        self._request = request

    @cached_property
    def orders(self) -> int:
        user = self._request.user
        if not user.is_authenticated:
            return 0
        return Order.objects.filter(owner=user).count()


def header_counters(request):
    return {"header_counters": HeaderCounters(request)}
