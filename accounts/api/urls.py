from django.urls import path
from rest_framework.routers import SimpleRouter

from . import admin_views, views

auth_urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("me/delete/", views.DeleteAccountView.as_view(), name="auth-delete-account"),
    path("password/change/", views.ChangePasswordView.as_view(), name="auth-password-change"),
    path("password/reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]

admin_router = SimpleRouter()
admin_router.register("customers", admin_views.CustomerViewSet, basename="admin-customer")
admin_router.register("staff", admin_views.StaffViewSet, basename="admin-staff")

admin_urlpatterns = [
    path("auth/csrf/", admin_views.AdminCsrfView.as_view(), name="admin-csrf"),
    path("auth/login/", admin_views.AdminLoginView.as_view(), name="admin-login"),
    path("auth/logout/", admin_views.AdminLogoutView.as_view(), name="admin-logout"),
    path("auth/me/", admin_views.AdminMeView.as_view(), name="admin-me"),
    *admin_router.urls,
]
