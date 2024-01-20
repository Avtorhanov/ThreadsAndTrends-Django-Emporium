# store/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.all_products, name='all-products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('about-us/', views.about_us, name='about-us'),
    # Добавьте URL-маршруты для аутентификации и других страниц
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)