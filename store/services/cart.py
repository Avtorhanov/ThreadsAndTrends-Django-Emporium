from store.models import Cart, CartItem, Product


def get_cart(request):
    if not request.user.is_authenticated:
        return None

    cart, _ = Cart.objects.get_or_create(owner=request.user)

    session_cart_products = request.session.get("cart_products", [])

    if session_cart_products:
        for product in Product.objects.live().filter(pk__in=session_cart_products):
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
            )

            if not created:
                cart_item.quantity += 1
                cart_item.save()

        del request.session["cart_products"]

    return cart


def add_product_to_cart(request, product_id):
    product = Product.objects.live().get(pk=product_id)

    if not request.user.is_authenticated:
        session_cart_products = request.session.get("cart_products", [])

        if product_id not in session_cart_products:
            session_cart_products.append(product_id)

        request.session["cart_products"] = session_cart_products

        return

    cart = get_cart(request)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
    )

    if not created:
        cart_item.quantity += 1

    cart_item.price_kopecks = product.price_kopecks
    cart_item.save()


def merge_session_cart_into_user_cart(request, user):
    session_cart_products = request.session.get("cart_products", [])

    if not session_cart_products:
        return

    cart, _ = Cart.objects.get_or_create(owner=user)

    # Удалённые и скрытые товары из гостевой корзины пропускаются.
    for product in Product.objects.live().filter(pk__in=session_cart_products):
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
        )

        if not created:
            cart_item.quantity += 1

        cart_item.price_kopecks = product.price_kopecks
        cart_item.save()

    del request.session["cart_products"]
