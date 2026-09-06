from store.models import Cart, CartItem, Product


def get_cart(request):
    if not request.user.is_authenticated:
        return None

    cart, _ = Cart.objects.get_or_create(
        owner=request.user
    )

    session_cart_products = request.session.get(
        'cart_products',
        []
    )

    if session_cart_products:
        for product_id in session_cart_products:
            product = Product.objects.get(pk=product_id)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
            )

            if not created:
                cart_item.quantity += 1
                cart_item.save()

        del request.session['cart_products']

    return cart

def add_product_to_cart(request, product_id):
    product = Product.objects.get(pk=product_id)

    if not request.user.is_authenticated:
        session_cart_products = request.session.get(
            'cart_products',
            []
        )

        if product_id not in session_cart_products:
            session_cart_products.append(product_id)

        request.session['cart_products'] = session_cart_products

        return

    cart = get_cart(request)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
    )

    if not created:
        cart_item.quantity += 1

    cart_item.price = product.price
    cart_item.save()

def merge_session_cart_into_user_cart(request, user):
    session_cart_products = request.session.get(
        'cart_products',
        []
    )

    if not session_cart_products:
        return

    cart, _ = Cart.objects.get_or_create(
        owner=user
    )

    for product_id in session_cart_products:
        product = Product.objects.get(pk=product_id)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
        )

        if not created:
            cart_item.quantity += 1

        cart_item.price = product.price
        cart_item.save()

    del request.session['cart_products']