from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API для мобильного приложения; новые версии подключаются отдельным namespace.
    path("api/v1/", include("core.api.urls", namespace="v1")),
    path("orders/", include("orders.urls")),
    path("", include("store.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
