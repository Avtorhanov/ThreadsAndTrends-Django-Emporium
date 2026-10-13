from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.api.urls import admin_urlpatterns, auth_urlpatterns
from orders.api.urls import admin_orders_urlpatterns, orders_urlpatterns
from store.api.urls import admin_catalog_urlpatterns, cart_urlpatterns, catalog_urlpatterns

from .views import HealthView

app_name = "v1"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="v1:schema"), name="docs"),
    # Мобильный клиент (JWT)
    path("auth/", include(auth_urlpatterns)),
    # Публичный каталог (без аутентификации)
    path("catalog/", include(catalog_urlpatterns)),
    # Корзина: клиент (JWT); расчёт гостевой корзины quote/ — без аутентификации
    path("cart/", include(cart_urlpatterns)),
    # Заказы клиента (JWT)
    path("orders/", include(orders_urlpatterns)),
    # Панель администратора (сессия + CSRF)
    path("admin/catalog/", include(admin_catalog_urlpatterns)),
    path("admin/", include(admin_orders_urlpatterns)),
    path("admin/", include(admin_urlpatterns)),
]
