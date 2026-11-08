from django.urls import path
from rest_framework.routers import SimpleRouter

from . import admin_summary, admin_views, views

orders_urlpatterns = [
    path("", views.OrderListCreateView.as_view(), name="orders"),
    path("checkout/", views.CheckoutPreviewView.as_view(), name="orders-checkout"),
    path("guest/", views.GuestCheckoutView.as_view(), name="orders-guest"),
    path("guest/preview/", views.GuestPreviewView.as_view(), name="orders-guest-preview"),
    path("guest/claim/", views.GuestClaimView.as_view(), name="orders-guest-claim"),
    path("guest/order/", views.GuestOrderView.as_view(), name="orders-guest-order"),
    path("guest/order/cancel/", views.GuestOrderCancelView.as_view(), name="orders-guest-cancel"),
    path("<str:number>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("<str:number>/cancel/", views.OrderCancelView.as_view(), name="order-cancel"),
]

admin_router = SimpleRouter()
admin_router.register("orders", admin_views.AdminOrderViewSet, basename="admin-order")

admin_orders_urlpatterns = [
    path("summary/", admin_summary.AdminSummaryView.as_view(), name="admin-summary"),
    *admin_router.urls,
]
