from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

content_urlpatterns = [
    path("articles/", views.ArticleListView.as_view(), name="content-articles"),
    path("articles/<slug:slug>/", views.ArticleDetailView.as_view(), name="content-article"),
    path("contacts/", views.ContactListView.as_view(), name="content-contacts"),
]

admin_router = SimpleRouter()
admin_router.register("articles", views.AdminArticleViewSet, basename="admin-content-article")
admin_router.register(
    "article-images", views.AdminArticleImageViewSet, basename="admin-content-article-image"
)
admin_router.register("blocks", views.AdminBlockViewSet, basename="admin-content-block")

admin_content_urlpatterns = [
    path("texts/<str:key>/", views.AdminSiteTextView.as_view(), name="admin-content-text"),
    path("settings/", views.AdminShopSettingsView.as_view(), name="admin-content-settings"),
    *admin_router.urls,
]
