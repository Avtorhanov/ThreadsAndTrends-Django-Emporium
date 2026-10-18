"""Легаси-витрина (шаблоны). Корзина — только в мобильном приложении (API /api/v1/cart/)."""

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from store.models import Category, Product


# Главная
def home(request):
    # До веб-витрины сессии 8 корень сайта может вести в веб-версию приложения (/app/).
    if settings.SITE_ROOT_REDIRECT:
        return redirect(settings.SITE_ROOT_REDIRECT)
    return render(request, "main/home.html")


# продукты
def all_products(request):
    products = Product.objects.live().with_stock().prefetch_related("images")
    page_number = request.GET.get("page")
    paginator = Paginator(products, 10)
    page_obj = paginator.get_page(page_number)
    categories = Category.objects.filter(is_active=True, parent__isnull=True)

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

    return render(
        request,
        "store/products.html",
        {
            "page_obj": page_obj,
            "categories": categories,
            "is_paginated": True,
            "start_page": start_page,
            "end_page": end_page,
        },
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.live().prefetch_related("images", "variants"), slug=slug
    )
    return render(request, "store/product_detail.html", {"product": product})


def category_detail(request, slug):
    category = get_object_or_404(
        Category.objects.filter(is_active=True).filter(
            Q(parent__isnull=True) | Q(parent__is_active=True)
        ),
        slug=slug,
    )
    children = category.children.filter(is_active=True)
    # Корневая категория показывает товары всех подкатегорий.
    products = (
        Product.objects.live()
        .with_stock()
        .filter(Q(category=category) | Q(category__parent=category))
        .prefetch_related("images")
    )
    return render(
        request,
        "store/category_detail.html",
        {"category": category, "children": children, "products": products},
    )


# логика поиска
def search_products(request):
    query = request.GET.get("q")
    products = Product.objects.live().with_stock().prefetch_related("images")

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    return render(request, "main/search_results.html", {"products": products})
