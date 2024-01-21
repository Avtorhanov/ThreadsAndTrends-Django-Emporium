# store/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import all_products, category_detail, subcategory_detail


urlpatterns = [
    path('', views.home, name='home'),
    path('products/', all_products, name='all-products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('about-us/', views.about_us, name='about-us'),

    path('category/<int:category_id>/', category_detail, name='category_detail'),
    path('subcategory/<int:subcategory_id>/', subcategory_detail, name='subcategory_detail'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
