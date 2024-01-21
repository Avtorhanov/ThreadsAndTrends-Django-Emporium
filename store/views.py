from django.shortcuts import render, get_object_or_404
from store.models import Product, Category, SubCategory

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
    categories = Category.objects.all()
    subcategories = SubCategory.objects.all()
    return render(request, 'store/products.html', {'products': products, 'categories': categories, 'subcategories': subcategories})

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
