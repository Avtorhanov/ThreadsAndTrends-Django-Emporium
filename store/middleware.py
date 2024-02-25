from .models import Order
from .utils import get_cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Получаем корзину пользователя
        cart = get_cart(request)
        # Получаем количество товаров в корзине
        cart_items_count = cart.cartitem_set.count() if cart else 0
        # Добавляем количество товаров в корзине в контекст каждого запроса
        request.cart_items_count = cart_items_count
        response = self.get_response(request)
        return response


class OrdersCountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            orders_count = Order.objects.filter(owner=request.user).count()
        else:
            orders_count = 0
        request.orders_count = orders_count
        response = self.get_response(request)
        return response