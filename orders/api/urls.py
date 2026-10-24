from django.urls import path
from rest_framework.routers import SimpleRouter

from . import admin_summary, admin_views, views

orders_urlpatterns = [
    path("", views.OrderListCreateView.as_view(), name="orders"),
    path("checkout/", views.CheckoutPreviewView.as_view(), name="orders-checkout"),
    path("<str:number>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("<str:number>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
]

admin_router = SimpleRouter()
admin_router.register("orders", admin_views.AdminOrderViewSet, basename="admin-order")

admin_orders_urlpatterns = [
    path("summary/", admin_summary.AdminSummaryView.as_view(), name="admin-summary"),
    *admin_router.urls,
]
