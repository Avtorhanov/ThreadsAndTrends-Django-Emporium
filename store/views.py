from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from store.models import Product, Category, SubCategory, Cart, CartItem, Order, OrderItem
from store.utils import get_cart, validate_checkout_data, create_order, create_order_with_items


# Главная
def home(request):
    return render(request, 'base/home.html')

# продукты
def product_detail(request, product_id):
    # Логика для отображения страницы товара
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

def all_products(request):
    products = Product.objects.all().order_by('-date')
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    return render(request, 'store/products.html', {'products': products, 'categories': categories, 'subcategories': subcategories})

# логика корзины
def add_to_cart(request, product_id):
    product = Product.objects.get(pk=product_id)
    cart = get_cart(request)

    if request.user.is_authenticated:
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    else:

        session_cart_products = request.session.get('cart_products', [])
        session_cart_products.append(product_id)
        request.session['cart_products'] = list(set(session_cart_products))
        messages.success(request, 'Товар добавлен в воображаемую корзину!')
        return JsonResponse({'status': 'success', 'message': 'Товар добавлен в корзину'})

    if not item_created:
        cart_item.quantity += 1
    cart_item.price = product.price
    cart_item.save()

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

# так чисто
def about_us(request):
    return render(request, 'base/about-us.html')

# представления для категорий и подкатегорий
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    subcategories = SubCategory.objects.filter(category=category)
    products = Product.objects.filter(category=category)
    return render(request, 'store/category_detail.html', {'category': category, 'subcategories': subcategories, 'products': products})

def subcategory_detail(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    products = Product.objects.filter(subcategory=subcategory)
    return render(request, 'store/subcategory_detail.html', {'subcategory': subcategory, 'products': products})

# логика поиска
def search_products(request):
    query = request.GET.get('q')
    if query:
        if query.isdigit() and len(query) <= 5:
            # Если запрос состоит из цифр и его длина не превышает 5 символов, ищем товары по их ID
            products = Product.objects.filter(id=int(query))
        else:
            # В противном случае выполняем простой поиск по полям name и description
            products = Product.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
    else:
        # Если запрос пустой, просто показываем все товары
        products = Product.objects.all()
    return render(request, 'base/search_results.html', {'products': products})

@login_required
def checkout(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    total_price = cart_item.product.price * cart_item.quantity

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')
        username = request.user.username

        validation_result = validate_checkout_data(full_name, username)
        if not validation_result['valid']:
            messages.error(request, validation_result['message'])
            return redirect('checkout', item_id=item_id)

        order = create_order(request.user, total_price, address, phone_number, full_name, cart_item)
        messages.success(request, 'Заказ оформлен!')
        return redirect('order_detail', order_id=order.id)

    return render(request, 'orders/checkout.html', {'cart_item': cart_item, 'total_price': total_price})

@login_required
def checkout_all(request):
    cart = Cart.objects.get(owner=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    total_price = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

        username = request.user.username

        validation_result = validate_checkout_data(full_name, username)
        if not validation_result['valid']:
            messages.error(request, validation_result['message'])
            return redirect('checkout_all')

        # Создаем заказ, включающий все товары из корзины
        order = create_order_with_items(request.user, address, phone_number, full_name, cart_items, total_price)

        # Очищаем корзину после оформления заказа
        cart_items.delete()

        messages.success(request, 'Заказ оформлен!')
        # Перенаправляем на страницу деталей заказа
        return redirect(reverse('order_detail', kwargs={'order_id': order.id}))

    return render(request, 'orders/checkout_all.html', {'cart_items': cart_items, 'total_price': total_price})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user)
    order_items = order.orderitem_set.all()
    return render(request, 'orders/order_detail.html', {'order': order, 'order_items': order_items})

@login_required
def my_orders(request):
    orders = Order.objects.filter(owner=request.user, is_ordered=True).order_by('-date_ordered')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, owner=request.user)
    order.delete()
    messages.success(request, 'Заказ удален!')
    return HttpResponseRedirect(reverse('my_orders'))