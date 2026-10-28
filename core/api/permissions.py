from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Администратор магазина (единственный продавец): активный is_staff."""

    message = "Доступно только администратору."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)


class HasSection(BasePermission):
    """Права сотрудника на раздел панели (accounts.staff): чтение — уровень view, изменение —
    edit. Раздел задаёт view атрибутом `section`; `read_also` — разделы, которым тоже можно
    читать эти данные (например, категории нужны списку товаров). Без `section` — только
    эндпоинты входа (тест проверяет, что у остальных раздел задан)."""

    message = "Нет доступа к этому разделу."

    def has_permission(self, request, view):
        section = getattr(view, "section", None)
        if section is None:
            return True
        from accounts import staff

        access = staff.access_for(request.user)
        need = staff.VIEW if request.method in SAFE_METHODS else staff.EDIT
        if access.allows(section, need):
            return True
        if need == staff.VIEW and any(
            access.allows(other, staff.VIEW) for other in getattr(view, "read_also", ())
        ):
            return True
        title = staff.ALL_SECTIONS.get(section, section)
        if need == staff.EDIT and access.allows(section, staff.VIEW):
            self.message = f"Раздел «{title}» доступен только для просмотра."
        else:
            self.message = f"Нет доступа к разделу «{title}»."
        return False


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
