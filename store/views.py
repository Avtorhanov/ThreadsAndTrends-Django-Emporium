from django.shortcuts import render, get_object_or_404
from store.models import Product


def home(request):
    # Логика для отображения главной страницы
    return render(request, 'store/home.html')

def product_detail(request, product_id):
    # Логика для отображения страницы товара
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

def cart(request):
    # Логика для отображения корзины
    # Добавьте логику для работы с содержимым корзины, если требуется
    return render(request, 'store/cart.html')

# Добавьте представления для аутентификации, регистрации и т. д.
def all_products(request):
    products = Product.objects.all()
    return render(request, 'store/products.html', {'products': products})

def about_us(request):
    return render(request, 'store/about-us.html')
