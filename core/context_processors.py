from functools import cached_property

from orders.models import Order
from store.models import CartItem


class HeaderCounters:
    """Счётчики шапки. Запросы к БД выполняются только при обращении из шаблона
    и не создают корзину (в отличие от прежнего CartMiddleware)."""

    def __init__(self, request):
        self._request = request

    @cached_property
    def cart(self) -> int:
        user = self._request.user
        if user.is_authenticated:
            return CartItem.objects.filter(cart__owner=user).count()
        return len(self._request.session.get("cart_products", []))

    @cached_property
    def orders(self) -> int:
        user = self._request.user
        if not user.is_authenticated:
            return 0
        return Order.objects.filter(owner=user).count()


def header_counters(request):
    return {"header_counters": HeaderCounters(request)}
