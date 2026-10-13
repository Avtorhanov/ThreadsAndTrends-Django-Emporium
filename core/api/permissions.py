from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Администратор магазина (единственный продавец): активный is_staff."""

    message = "Доступно только администратору."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class IsOwner(BasePermission):
    """Объект принадлежит текущему пользователю.

    Поле владельца задаётся во view атрибутом owner_field (по умолчанию "owner");
    "self" — объектом является сам пользователь. Список объектов всё равно
    фильтруется в get_queryset: эта проверка — вторая линия защиты.
    """

    message = "Нет доступа к чужому объекту."

    def has_object_permission(self, request, view, obj):
        field = getattr(view, "owner_field", "owner")
        owner_id = obj.pk if field == "self" else getattr(obj, f"{field}_id", None)
        return bool(request.user and request.user.is_authenticated and owner_id == request.user.pk)
