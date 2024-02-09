
from django.contrib.auth.signals import user_logged_in

from store.models import Product, CartItem, Cart, Order, OrderItem


def get_cart(request):
    if request.user.is_authenticated:
        # Если пользователь аутентифицирован, получаем его корзину
        user = request.user
        cart, created = Cart.objects.get_or_create(owner=user)

        # Переносим продукты из сеанса в корзину пользователя, если они есть
        session_cart_products = request.session.get('cart_products', [])
        if session_cart_products:
            # Переносим продукты из сеанса в корзину пользователя
            for product_id in session_cart_products:
                product = Product.objects.get(pk=product_id)
                cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
                # Увеличиваем количество продуктов, если они уже есть в корзине пользователя
                cart_item.quantity += 1
                cart_item.save()

            # Очищаем список продуктов в сеансе
            del request.session['cart_products']
    else:
        # Если пользователь не аутентифицирован, получаем или создаем корзину по сеансу
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, created = Cart.objects.get_or_create(session_key=session_key)

    return cart


def store_cart_in_session(sender, user, request, **kwargs):
    # При успешной аутентификации сохраняем продукты из корзины в сессии
    session_cart_products = request.session.get('cart_products', [])
    if session_cart_products:
        user_cart = Cart.objects.get_or_create(owner=user)[0]
        for product_id in session_cart_products:
            product = Product.objects.get(pk=product_id)
            cart_item, _ = CartItem.objects.get_or_create(cart=user_cart, product=product)
            # Увеличиваем количество продуктов, если они уже есть в корзине пользователя
            #cart_item.quantity -= 1
            cart_item.save()

        # Очищаем список продуктов в сессии
        del request.session['cart_products']
# Привязываем сигнал к функции, которая будет вызываться после успешной аутентификации
user_logged_in.connect(store_cart_in_session)


# оформление заказа
def validate_checkout_data(full_name, username):
    if full_name != username:
        return {'valid': False, 'message': 'Пожалуйста, введите ваше имя правильно.'}
    return {'valid': True}

def create_order(user, total_price, address, phone_number, full_name, cart_item):
    order = Order.objects.create(
        owner=user,
        total_price=total_price,
        address=address,
        phone_number=phone_number,
        full_name=full_name,
        is_ordered=True
    )
    OrderItem.objects.create(order=order, product=cart_item.product, quantity=cart_item.quantity, price=cart_item.price)
    cart_item.delete()
    return order