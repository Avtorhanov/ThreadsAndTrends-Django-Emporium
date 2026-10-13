from django.contrib import admin
from django.contrib.admin.apps import AdminConfig


class SuperuserAdminSite(admin.AdminSite):
    """Стандартная Django admin — только запасной вход суперпользователя.
    Повседневная работа администратора — в собственной панели (admin-panel/)."""

    site_header = "DiDi-shop: резервная админка"
    site_title = "DiDi-shop"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


class SuperuserAdminConfig(AdminConfig):
    default_site = "core.admin.SuperuserAdminSite"
