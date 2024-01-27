# store/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import all_products, category_detail, subcategory_detail, cart_view, add_to_cart, update_cart, remove_from_cart

urlpatterns = [
    path('', views.home, name='home'),

    path('products/', all_products, name='all-products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('about-us/', views.about_us, name='about-us'),

    path('add_to_cart/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('update_cart_item/<int:item_id>/<int:new_count>/', update_cart, name='update_cart_item'),
    path('remove_from_cart/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    # Просмотр корзины пользователя
    path('cart/', cart_view, name='cart'),

    path('category/<int:category_id>/', category_detail, name='category_detail'),
    path('subcategory/<int:subcategory_id>/', subcategory_detail, name='subcategory_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
