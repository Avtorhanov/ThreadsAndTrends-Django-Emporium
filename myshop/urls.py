from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# Витрина (веб-версия приложения) и панель администратора — статические сборки, их раздаёт
# Caddy в продакшене (deploy/Caddyfile). Django обслуживает только API и резервную админку.
urlpatterns = [
    path("admin/", admin.site.urls),
    # API для мобильного приложения; новые версии подключаются отдельным namespace.
    path("api/v1/", include("core.api.urls", namespace="v1")),
    # Локально (runserver) корень ведёт в документацию API.
    path("", RedirectView.as_view(url="/api/v1/docs/", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
