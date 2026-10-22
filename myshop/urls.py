from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API для мобильного приложения; новые версии подключаются отдельным namespace.
    path("api/v1/", include("core.api.urls", namespace="v1")),
    # Веб-витрина: каталог, корзина, оформление, кабинет, sitemap.xml и robots.txt.
    path("", include("web.urls")),
]

handler404 = "web.views.errors.not_found"
handler500 = "web.views.errors.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
