from .services import get_cart

class CartMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            cart = get_cart(request)
            cart_items_count = cart.cartitem_set.count()
        else:
            cart_items_count = len(
                request.session.get(
                    'cart_products',
                    []
                )
            )

        request.cart_items_count = cart_items_count

        return self.get_response(request)

       