from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import HealthView

app_name = "v1"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="v1:schema"), name="docs"),
]
