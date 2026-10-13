from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.api.urls import admin_urlpatterns, auth_urlpatterns

from .views import HealthView

app_name = "v1"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="v1:schema"), name="docs"),
    # Мобильный клиент (JWT)
    path("auth/", include(auth_urlpatterns)),
    # Панель администратора (сессия + CSRF)
    path("admin/", include(admin_urlpatterns)),
]
