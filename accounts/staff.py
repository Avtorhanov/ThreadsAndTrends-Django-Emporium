"""Сотрудники панели и права по разделам.

Владелец (суперпользователь) и администратор без записи StaffAccess — без ограничений;
только им доступны «Настройки и оплата» и «Сотрудники». Приглашённый сотрудник получает
права по разделам: none (раздела нет в панели), view (только чтение), edit.

Права проверяет сервер на каждом эндпоинте панели (core.api.permissions.HasSection);
панель лишь скрывает недоступные разделы.
"""

from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string

from core.tasks import send_email

from . import services
from .models import StaffAccess, User, normalize_email

NONE, VIEW, EDIT = "none", "view", "edit"
LEVELS = (NONE, VIEW, EDIT)
LEVEL_CHOICES = [(NONE, "Нет доступа"), (VIEW, "Смотреть"), (EDIT, "Менять")]
_RANK = {NONE: 0, VIEW: 1, EDIT: 2}

# Разделы, которые владелец может открыть сотруднику (порядок — как в панели).
SECTIONS: dict[str, str] = {
    "summary": "Сводка и выручка",
    "orders": "Заказы",
    "products": "Товары и статусы",
    "categories": "Категории",
    "articles": "Статьи",
    "storefront": "Главная и тема",
    "customers": "Клиенты",
}
# Только владелец: сотруднику не выдаются.
OWNER_SECTIONS: dict[str, str] = {
    "settings": "Настройки и оплата",
    "staff": "Сотрудники",
}
ALL_SECTIONS = {**SECTIONS, **OWNER_SECTIONS}

PRESETS: dict[str, dict[str, str]] = {
    "orders_manager": {"summary": VIEW, "orders": EDIT, "products": VIEW, "customers": VIEW},
    "content": {
        "products": VIEW,
        "categories": VIEW,
        "articles": EDIT,
        "storefront": EDIT,
    },
    "all": dict.fromkeys(SECTIONS, EDIT),
}

INVITE_TTL = timedelta(days=3)


@dataclass(frozen=True)
class Access:
    is_owner: bool
    levels: dict[str, str]

    def level(self, section: str) -> str:
        if self.is_owner:
            return EDIT
        if section in OWNER_SECTIONS:
            return NONE
        return self.levels.get(section, NONE)

    def allows(self, section: str, need: str) -> bool:
        return _RANK[self.level(section)] >= _RANK[need]

    def as_dict(self) -> dict[str, str]:
        return {section: self.level(section) for section in ALL_SECTIONS}


OWNER = Access(is_owner=True, levels={})


def clean_permissions(raw: dict) -> dict[str, str]:
    """Только известные разделы сотрудника и уровни; отсутствующий раздел — none."""
    if not isinstance(raw, dict):
        raise ValidationError({"permissions": "Права — словарь «раздел: уровень»."})
    unknown = [key for key in raw if key not in SECTIONS]
    if unknown:
        raise ValidationError({"permissions": f"Неизвестные разделы: {', '.join(unknown)}."})
    bad = [key for key, value in raw.items() if value not in LEVELS]
    if bad:
        raise ValidationError({"permissions": "Уровень доступа: none, view или edit."})
    return {section: raw.get(section, NONE) for section in SECTIONS}


def access_for(user) -> Access:
    """Права пользователя панели (запоминаются на объекте пользователя на время запроса)."""
    cached = getattr(user, "_staff_access", None)
    if cached is not None:
        return cached
    if user.is_superuser:
        access = OWNER
    else:
        record = StaffAccess.objects.filter(user=user).only("permissions").first()
        access = OWNER if record is None else Access(False, clean_levels(record.permissions))
    user._staff_access = access
    return access


def clean_levels(raw: dict) -> dict[str, str]:
    # Сохранённые права могли устареть (раздел убрали) — неизвестное отбрасывается.
    return {k: v for k, v in (raw or {}).items() if k in SECTIONS and v in LEVELS}


def is_owner(user) -> bool:
    return access_for(user).is_owner


def staff_queryset():
    return User.objects.alive().filter(is_staff=True).select_related("staff_access")


def _require_owner(actor) -> None:
    if not is_owner(actor):
        raise PermissionDenied("Сотрудниками управляет только владелец.")


def _send_invite(user: User, code: str, inviter: User) -> None:
    confirm = f"{settings.SITE_URL}/password-reset/confirm/?{urlencode({'email': user.email})}"
    body = render_to_string(
        "accounts/email/staff_invite.txt",
        {
            "user": user,
            "code": code,
            "link": confirm,
            "panel": f"{settings.SITE_URL}/panel/",
            "inviter": inviter.get_full_name() or inviter.email,
            "days": INVITE_TTL.days,
        },
    )
    recipient = user.email
    transaction.on_commit(
        lambda: send_email.enqueue("DiDi-shop: приглашение в панель магазина", body, [recipient])
    )


@transaction.atomic
def invite(actor, *, email: str, first_name: str = "", permissions: dict) -> User:
    """Новый сотрудник: учётная запись без пароля + код, по которому он сам задаст пароль."""
    _require_owner(actor)
    levels = clean_permissions(permissions)
    email = normalize_email(email)
    if User.objects.filter(email=email).exists():
        raise ValidationError({"email": "Пользователь с таким email уже есть."})
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email, password=None, first_name=first_name.strip(), is_staff=True
            )
    except IntegrityError as exc:
        raise ValidationError({"email": "Пользователь с таким email уже есть."}) from exc
    StaffAccess.objects.create(user=user, permissions=levels, invited_by=actor)
    _send_invite(user, services.issue_reset_code(user, INVITE_TTL), actor)
    return user


def _target(actor, user: User) -> StaffAccess:
    _require_owner(actor)
    if user.pk == actor.pk:
        raise ValidationError("Свои права и доступ изменить нельзя.")
    record = StaffAccess.objects.select_for_update().filter(user=user).first()
    if record is None or user.is_superuser:
        raise ValidationError("Права владельца не меняются.")
    return record


@transaction.atomic
def update(
    actor,
    user: User,
    *,
    permissions: dict | None = None,
    is_active: bool | None = None,
    first_name: str | None = None,
) -> User:
    record = _target(actor, user)
    if permissions is not None:
        record.permissions = clean_permissions(permissions)
        record.save(update_fields=["permissions", "updated_at"])
    fields = []
    if first_name is not None:
        user.first_name = first_name.strip()
        fields.append("first_name")
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        fields.append("is_active")
        if not is_active:
            # Неактивного сессия не пускает (ModelBackend.get_user); токены приложения — отзываем.
            transaction.on_commit(lambda: services.revoke_all_refresh_tokens(user))
    if fields:
        user.save(update_fields=fields)
    return staff_queryset().get(pk=user.pk)


@transaction.atomic
def resend_invite(actor, user: User) -> None:
    _target(actor, user)
    if user.has_usable_password():
        raise ValidationError("Сотрудник уже задал пароль.")
    _send_invite(user, services.issue_reset_code(user, INVITE_TTL), actor)
