from .utils import get_cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # �������� ������� ������������
        cart = get_cart(request)
        # �������� ���������� ������� � �������
        cart_items_count = cart.cartitem_set.count() if cart else 0
        # ��������� ���������� ������� � ������� � �������� ������� �������
        request.cart_items_count = cart_items_count
        response = self.get_response(request)
        return response