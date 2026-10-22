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

admin_content_urlpatterns = admin_router.urls
