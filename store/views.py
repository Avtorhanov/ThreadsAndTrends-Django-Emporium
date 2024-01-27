from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from store.models import Product, Category, SubCategory, Cart, CartItem


def home(request):
    # Логика для отображения главной страницы
    return render(request, 'store/home.html')

def product_detail(request, product_id):
    # Логика для отображения страницы товара
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

def all_products(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()

    return render(request, 'store/products.html', {'products': products, 'categories': categories, 'subcategories': subcategories})

def add_to_cart(request, product_id):
    # Получаем продукт
    product = Product.objects.get(pk=product_id)

    if request.user.is_authenticated:
        user = request.user
        cart, created = Cart.objects.get_or_create(owner=user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart, created = Cart.objects.get_or_create(session_key=session_key)

    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, 'Товар добавлен в корзину!')
    return JsonResponse({'status': 'success', 'message': 'Товар добавлен в корзину'})


@login_required
def cart_view(request):
    user = request.user
    cart, created = Cart.objects.get_or_create(owner=user)
    cart_items = cart.cartitem_set.all()  # Используйте related name, если вы его задали
    total_price = sum(item.price * item.quantity for item in cart_items)

    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total_price': total_price})

def update_cart(request, item_id, new_count):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.quantity = new_count
    cart_item.save()
    total_price = cart_item.cart.calculate_total_price()  # Предполагается, что у вашей модели Cart есть метод calculate_total_price(), который возвращает общую стоимость корзины
    return JsonResponse({'total_price': total_price})

def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, f'Товар удален из корзины!')
    return JsonResponse({'status': 'success', 'message': 'Товар удален из корзины'})
# Добавьте представления для аутентификации, регистрации и т. д.

def about_us(request):
    return render(request, 'store/about-us.html')

# Добавлены представления для категорий и подкатегорий
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    subcategories = SubCategory.objects.filter(category=category)
    products = Product.objects.filter(category=category)
    return render(request, 'store/category_detail.html', {'category': category, 'subcategories': subcategories, 'products': products})

def subcategory_detail(request, subcategory_id):
    subcategory = get_object_or_404(SubCategory, id=subcategory_id)
    products = Product.objects.filter(subcategory=subcategory)
    return render(request, 'store/subcategory_detail.html', {'subcategory': subcategory, 'products': products})

