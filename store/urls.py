# store/urls.py
from django.urls import path
from . import views
urlpatterns = [
    
    # основные
    path('', views.home, name='home'),
    path('products/', views.all_products, name='all-products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),

    # Просмотр корзины пользователя
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update_cart_item/<int:item_id>/<int:new_count>/', views.update_cart, name='update_cart_item'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.cart_view, name='cart'),

    # Категории
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('subcategory/<int:subcategory_id>/', views.subcategory_detail, name='subcategory_detail'),

    # поиск
    path('search/', views.search_products, name='search_products'),
]
