# store/urls.py
from django.urls import path

from . import views

urlpatterns = [
    # основные
    path("", views.home, name="home"),
    path("products/", views.all_products, name="all-products"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    # Категории
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    # поиск
    path("search/", views.search_products, name="search_products"),
]
