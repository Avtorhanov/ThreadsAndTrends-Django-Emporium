from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from carts.models import CartItem, Cart
from carts.utils import get_cart, store_cart_in_session
from store.models import Product


# Create your views here.
def add_to_cart(request, product_id):
    product = Product.objects.get(pk=product_id)
    cart = get_cart(request)

    if request.user.is_authenticated:
        # Если пользователь аутентифицирован, добавляем продукт в его корзину
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not item_created:
            cart_item.quantity += 1
            cart_item.save()
    else:
        # Если пользователь не аутентифицирован, сохраняем продукт в сессии
        session_cart_products = request.session.get('cart_products', [])
        session_cart_products.append(product_id)
        request.session['cart_products'] = list(set(session_cart_products))  # Избавляемся от дубликатов
        messages.success(request, 'Товар добавлен в воображаемую корзину!')
        return JsonResponse({'status': 'success', 'message': 'Товар добавлен в корзину'})

    messages.success(request, 'Товар добавлен в корзину!')
    return JsonResponse({'status': 'success', 'message': 'Товар добавлен в корзину'})



@login_required
def cart_view(request):
    user = request.user
    cart, created = Cart.objects.get_or_create(owner=user)
    cart_items = cart.cartitem_set.all()
    total_price = sum(item.price * item.quantity for item in cart_items)

    return render(request, 'orders/cart.html', {'cart_items': cart_items, 'total_price': total_price})

def update_cart(request, item_id, new_count):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.quantity = new_count
    cart_item.save()
    total_price = cart_item.cart.calculate_total_price()
    return JsonResponse({'total_price': total_price})

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, f'Товар удален из корзины!')
    return JsonResponse({'status': 'success', 'message': 'Товар удален из корзины'})
