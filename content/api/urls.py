from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

content_urlpatterns = [
    path("articles/", views.ArticleListView.as_view(), name="content-articles"),
    path("articles/<slug:slug>/", views.ArticleDetailView.as_view(), name="content-article"),
    path("contacts/", views.ContactListView.as_view(), name="content-contacts"),
    path("home/", views.HomeView.as_view(), name="content-home"),
    path("theme/", views.ShopThemeView.as_view(), name="content-theme"),
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
    path("theme/", views.AdminThemeView.as_view(), name="admin-content-theme"),
    path("home/", views.AdminHomeView.as_view(), name="admin-content-home"),
    path("home/publish/", views.AdminHomePublishView.as_view(), name="admin-content-home-publish"),
    path("home/reorder/", views.AdminHomeReorderView.as_view(), name="admin-content-home-reorder"),
    path(
        "home/blocks/",
        views.AdminHomeBlockCreateView.as_view(),
        name="admin-content-home-blocks",
    ),
    path(
        "home/blocks/<int:pk>/",
        views.AdminHomeBlockView.as_view(),
        name="admin-content-home-block",
    ),
    path(
        "home/blocks/<int:pk>/image/",
        views.AdminHomeBlockImageView.as_view(),
        name="admin-content-home-block-image",
    ),
    *admin_router.urls,
]
