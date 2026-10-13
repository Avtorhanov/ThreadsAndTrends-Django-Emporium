from django.urls import path
from rest_framework.routers import SimpleRouter

from . import admin_views, cart_views, views

catalog_urlpatterns = [
    path("categories/", views.CategoryTreeView.as_view(), name="catalog-categories"),
    path("products/", views.ProductListView.as_view(), name="catalog-products"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="catalog-product"),
]

cart_urlpatterns = [
    path("", cart_views.CartView.as_view(), name="cart"),
    path("items/", cart_views.CartItemsView.as_view(), name="cart-items"),
    path("items/<int:pk>/", cart_views.CartItemView.as_view(), name="cart-item"),
    path("ack-prices/", cart_views.CartAckPricesView.as_view(), name="cart-ack-prices"),
    path("merge/", cart_views.CartMergeView.as_view(), name="cart-merge"),
    path("quote/", cart_views.CartQuoteView.as_view(), name="cart-quote"),
]

admin_router = SimpleRouter()
admin_router.register(
    "categories", admin_views.AdminCategoryViewSet, basename="admin-catalog-category"
)
admin_router.register("products", admin_views.AdminProductViewSet, basename="admin-catalog-product")
admin_router.register("variants", admin_views.AdminVariantViewSet, basename="admin-catalog-variant")
admin_router.register("images", admin_views.AdminImageViewSet, basename="admin-catalog-image")

admin_catalog_urlpatterns = admin_router.urls
