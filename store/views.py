from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from store.models import CartItem, Category, Product
from store.services import add_product_to_cart, get_cart


# Главная
def home(request):
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


# логика корзины
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product.objects.live(), pk=product_id)

    add_product_to_cart(
        request,
        product.id,
    )

    messages.success(
        request,
        "Товар добавлен в корзину!",
    )

    return JsonResponse(
        {
            "status": "success",
            "message": "Товар добавлен в корзину",
        }
    )


@login_required
def cart_view(request):
    cart = get_cart(request)

    cart_items = cart.cartitem_set.select_related("product")

    total_kopecks = sum(item.price_kopecks * item.quantity for item in cart_items)

    return render(
        request,
        "orders/cart.html",
        {
            "cart_items": cart_items,
            "total_kopecks": total_kopecks,
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
    cart_item.save(update_fields=["quantity"])

    return JsonResponse({"total_kopecks": cart_item.cart.calculate_total_kopecks()})


@login_required
@require_POST
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__owner=request.user,
    )

    cart_item.delete()

    messages.success(request, "Товар удален из корзины!")

    return JsonResponse(
        {
            "status": "success",
            "message": "Товар удален из корзины",
        }
    )


# логика поиска
def search_products(request):
    query = request.GET.get("q")
    products = Product.objects.live().with_stock().prefetch_related("images")

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    return render(request, "main/search_results.html", {"products": products})
