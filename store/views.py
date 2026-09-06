# -*- coding: utf-8 -*-

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from store.models import Product, Category, SubCategory, Cart, CartItem
from store.services import (get_cart, add_product_to_cart)
from django.views.decorators.http import require_POST

# Главная
def home(request):
    return render(request, 'main/home.html')

# продукты
def all_products(request):
    products = Product.objects.all().order_by('-date')
    page_number = request.GET.get('page')
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.all()

    # Рассчитываем значения страниц
    if page_obj.number <= 2:
        start_page = 1
        end_page = min(3, paginator.num_pages)
    elif page_obj.number >= paginator.num_pages - 1:
        start_page = max(paginator.num_pages - 2, 1)
        end_page = paginator.num_pages
    else:
        start_page = page_obj.number - 1
        end_page = page_obj.number + 1

    return render(request, 'store/products.html', {'page_obj': page_obj, 'categories': categories, 'is_paginated': True, 'start_page': start_page, 'end_page': end_page})

def product_detail(request, product_id):
    # Логика для отображения страницы товара
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})

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

# логика корзины
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    add_product_to_cart(
        request,
        product.id,
    )

    messages.success(
        request,
        'Товар добавлен в корзину!',
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Товар добавлен в корзину',
    })

@login_required
def cart_view(request):
    cart = get_cart(request)

    cart_items = cart.cartitem_set.select_related(
        'product'
    )

    total_price = sum(
        item.price * item.quantity
        for item in cart_items
    )

    return render(
        request,
        'orders/cart.html',
        {
            'cart_items': cart_items,
            'total_price': total_price,
        },
    )

@login_required
@require_POST
def update_cart(request, item_id, new_count):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__owner=request.user,
    )

    cart_item.quantity = new_count
    cart_item.save(update_fields=['quantity'])

    total_price = cart_item.cart.calculate_total_price()

    return JsonResponse({
        'total_price': total_price
    })

@login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__owner=request.user,
    )

    cart_item.delete()

    messages.success(request, 'Товар удален из корзины!')

    return JsonResponse({
        'status': 'success',
        'message': 'Товар удален из корзины',
    })

# логика поиска
def search_products(request):
    query = request.GET.get('q')
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    return render(request, 'main/search_results.html', {'products': products})

