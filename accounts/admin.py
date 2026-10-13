from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from . import services
from .models import User


class EmailUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes: dict = {}


class EmailUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
        field_classes: dict = {}


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Резервная админка суперпользователя. Удаление — только мягкое."""

    form = EmailUserChangeForm
    add_form = EmailUserCreationForm
    ordering = ["-date_joined"]
    list_display = ["email", "first_name", "last_name", "is_staff", "is_active", "deleted_at"]
    list_filter = [
        "is_staff",
        "is_superuser",
        "is_active",
        ("deleted_at", admin.EmptyFieldListFilter),
    ]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["last_login", "date_joined", "deleted_at"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("first_name", "last_name")}),
        (
            "Права",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Даты", {"fields": ("last_login", "date_joined", "deleted_at")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
    actions = ["soft_delete_selected"]

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Удалить (мягко, с анонимизацией)")
    def soft_delete_selected(self, request, queryset):
        count = 0
        for user in queryset.filter(deleted_at__isnull=True):
            if user.pk == request.user.pk:
                continue
            services.soft_delete_user(user)
            count += 1
        self.message_user(request, f"Удалено пользователей: {count}", messages.SUCCESS)
