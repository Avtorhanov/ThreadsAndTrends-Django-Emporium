from django.urls import path
from orders import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/<int:item_id>/', views.checkout, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('delete_order/<int:order_id>/', views.delete_order, name='delete_order'),
    path('checkout-all/', views.checkout_all, name='checkout_all'),

]