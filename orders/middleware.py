from orders.models import Order


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