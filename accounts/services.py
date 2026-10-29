"""Бизнес-логика пользователей. Views только валидируют ввод и вызывают эти функции.

Ошибки ввода — django.core.exceptions.ValidationError (словарь поле → сообщения),
нарушение прав — django.core.exceptions.PermissionDenied. Обработчик исключений API
(core.api.exceptions) превращает их в 400/403.
"""

import logging
import secrets
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core.tasks import send_email

from .models import PasswordResetCode, User, normalize_email
from .signals import account_deleted, account_deleting

logger = logging.getLogger(__name__)

AVATAR_SIZE = 320  # px, квадрат: в профиле — до 96 px, запас на экраны 3x
AVATAR_QUALITY = 82

RESET_CODE_TTL = timedelta(minutes=15)
RESET_CODE_MAX_ATTEMPTS = 5
RESET_CODE_RESEND_COOLDOWN = timedelta(seconds=60)
RESET_CODES_PER_HOUR = 5
INVALID_RESET_CODE = "Неверный или просроченный код."


# --- Токены ---


def issue_tokens(user: User) -> dict[str, str]:
    """Пара JWT для мобильного клиента. Refresh попадает в OutstandingToken (для отзыва)."""
    refresh = RefreshToken.for_user(user)
    update_last_login(None, user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def revoke_all_refresh_tokens(user: User) -> int:
    """Выход на всех устройствах. Access-токены дополнительно инвалидирует
    CHECK_REVOKE_TOKEN (хэш пароля в токене) и проверка is_active."""
    outstanding = OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)
    created = BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding], ignore_conflicts=True
    )
    return len(created)


def logout(user: User | None, refresh_token: str) -> None:
    """Отзыв одного refresh-токена (выход на текущем устройстве)."""
    try:
        token = RefreshToken(refresh_token)
    except TokenError as exc:
        raise ValidationError({"refresh": "Токен недействителен или уже отозван."}) from exc
    if user is not None and str(token.get("user_id")) != str(user.pk):
        raise ValidationError({"refresh": "Токен недействителен или уже отозван."})
    token.blacklist()


# --- Регистрация, вход, профиль ---


def register_customer(
    *, email: str, password: str, first_name: str = "", last_name: str = ""
) -> User:
    email = normalize_email(email)
    if User.objects.filter(email=email).exists():
        raise ValidationError({"email": "Пользователь с таким email уже зарегистрирован."})

    user = User(email=email, first_name=first_name, last_name=last_name)
    _validate_new_password(password, user)
    user.set_password(password)
    try:
        user.save()
    except IntegrityError as exc:  # параллельная регистрация того же email
        raise ValidationError({"email": "Пользователь с таким email уже зарегистрирован."}) from exc
    logger.info("Зарегистрирован клиент %s", user.pk)
    return user


def authenticate_user(*, email: str, password: str) -> User | None:
    """None для неверных данных, заблокированных и удалённых (is_active=False)."""
    return authenticate(request=None, email=normalize_email(email), password=password)


def update_profile(user: User, **fields) -> User:
    allowed = {"first_name", "last_name"}
    changed = [name for name in fields if name in allowed]
    for name in changed:
        setattr(user, name, fields[name])
    if changed:
        user.save(update_fields=changed)
    return user


# --- Фото профиля ---


def _avatar_webp(uploaded) -> ContentFile:
    """Квадрат AVATAR_SIZE по центру, WebP. Перекодирование убирает EXIF (геометку с телефона)."""
    try:
        with Image.open(uploaded) as source:
            picture = ImageOps.exif_transpose(source)
            picture = picture.convert("RGBA" if picture.mode in ("RGBA", "LA", "P") else "RGB")
            picture = ImageOps.fit(picture, (AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            picture.save(buffer, "WEBP", quality=AVATAR_QUALITY, method=4)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError({"avatar": "Файл не является изображением."}) from exc
    return ContentFile(buffer.getvalue(), name="avatar.webp")


def _delete_file_after_commit(storage, name: str) -> None:
    if name:
        transaction.on_commit(lambda: storage.delete(name))


def set_avatar(user: User, uploaded) -> User:
    """Новое фото профиля (JPEG/PNG/WebP до 5 МБ — та же проверка, что у фото товаров).
    Прежний файл удаляется после commit."""
    from store.services.catalog import inspect_image  # общая проверка изображений

    try:
        inspect_image(uploaded)
    except ValidationError as exc:
        raise ValidationError({"avatar": exc.message_dict.get("image", exc.messages)}) from exc
    content = _avatar_webp(uploaded)
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        old = user.avatar.name
        user.avatar.save(content.name, content, save=False)
        user.save(update_fields=["avatar"])
        _delete_file_after_commit(user.avatar.storage, old)
    return user


def remove_avatar(user: User) -> User:
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        old = user.avatar.name
        if old:
            user.avatar = ""
            user.save(update_fields=["avatar"])
            _delete_file_after_commit(user.avatar.storage, old)
    return user


def change_password(user: User, *, old_password: str, new_password: str) -> dict[str, str]:
    """Смена пароля со старым паролем. Остальные устройства разлогиниваются,
    текущему возвращается новая пара токенов."""
    if not user.check_password(old_password):
        raise ValidationError({"old_password": "Неверный текущий пароль."})
    _validate_new_password(new_password, user, field="new_password")
    user.set_password(new_password)
    user.save(update_fields=["password"])
    revoke_all_refresh_tokens(user)
    return issue_tokens(user)


def _validate_new_password(password: str, user: User, field: str = "password") -> None:
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise ValidationError({field: exc.messages}) from exc


# --- Сброс пароля по коду из письма ---


def _hash_reset_code(user_id: int, code: str) -> str:
    return salted_hmac("accounts.password_reset", f"{user_id}:{code}").hexdigest()


def issue_reset_code(user: User, ttl: timedelta) -> str:
    """Новый одноразовый код (действует только последний). Вызывать внутри транзакции."""
    now = timezone.now()
    code = f"{secrets.randbelow(10**6):06d}"
    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    PasswordResetCode.objects.create(
        user=user, code_hash=_hash_reset_code(user.pk, code), expires_at=now + ttl
    )
    return code


def request_password_reset(email: str) -> None:
    """Всегда завершается без ошибки: ответ не раскрывает, есть ли такой email."""
    user = User.objects.alive().filter(email=normalize_email(email), is_active=True).first()
    if user is None:
        return

    now = timezone.now()
    recent = PasswordResetCode.objects.filter(user=user, created_at__gte=now - timedelta(hours=1))
    if recent.count() >= RESET_CODES_PER_HOUR:
        logger.warning("Сброс пароля: превышен лимит кодов для пользователя %s", user.pk)
        return
    if recent.filter(created_at__gte=now - RESET_CODE_RESEND_COOLDOWN).exists():
        return

    with transaction.atomic():
        code = issue_reset_code(user, RESET_CODE_TTL)
        body = render_to_string(
            "accounts/email/password_reset.txt",
            {"user": user, "code": code, "ttl_minutes": int(RESET_CODE_TTL.total_seconds() // 60)},
        )
        transaction.on_commit(
            lambda: send_email.enqueue("DiDi-shop: код для сброса пароля", body, [user.email])
        )


def confirm_password_reset(*, email: str, code: str, new_password: str) -> dict[str, str]:
    user = User.objects.alive().filter(email=normalize_email(email), is_active=True).first()
    if user is None:
        raise ValidationError({"code": INVALID_RESET_CODE})

    _validate_new_password(new_password, user, field="new_password")

    now = timezone.now()
    with transaction.atomic():
        record = (
            PasswordResetCode.objects.select_for_update()
            .filter(user=user, used_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if record is None or record.attempts >= RESET_CODE_MAX_ATTEMPTS:
            valid = False
        elif constant_time_compare(_hash_reset_code(user.pk, code), record.code_hash):
            valid = True
            record.used_at = now
            record.save(update_fields=["used_at"])
            user.set_password(new_password)
            user.save(update_fields=["password"])
            revoke_all_refresh_tokens(user)
        else:
            # Счётчик сохраняется: исключение бросаем после выхода из транзакции.
            valid = False
            record.attempts += 1
            record.save(update_fields=["attempts"])

    if not valid:
        raise ValidationError({"code": INVALID_RESET_CODE})
    logger.info("Пароль сброшен по коду для пользователя %s", user.pk)
    return issue_tokens(user)


# --- Удаление и блокировка ---


def delete_own_account(user: User, *, password: str) -> None:
    if user.is_staff or user.is_superuser:
        raise PermissionDenied("Учётную запись администратора нельзя удалить из приложения.")
    if not user.check_password(password):
        raise ValidationError({"password": "Неверный пароль."})
    soft_delete_user(user)


def soft_delete_user(user: User) -> User:
    """Мягкое удаление с анонимизацией. Заказы остаются для учёта (персональные данные
    в них обезличивает приложение orders), вход и восстановление пароля невозможны,
    все refresh-токены отозваны."""
    if user.is_deleted:
        return user
    account_deleting.send(sender=User, user=user)  # приёмники могут запретить удаление
    with transaction.atomic():
        user.deleted_at = timezone.now()
        user.is_active = False
        user.email = f"deleted-{user.pk}@deleted.invalid"
        user.first_name = ""
        user.last_name = ""
        avatar = user.avatar.name
        user.avatar = ""
        user.set_unusable_password()
        user.save(
            update_fields=[
                "deleted_at",
                "is_active",
                "email",
                "first_name",
                "last_name",
                "avatar",
                "password",
            ]
        )
        _delete_file_after_commit(user.avatar.storage, avatar)
        PasswordResetCode.objects.filter(user=user).delete()
        revoke_all_refresh_tokens(user)
        account_deleted.send(sender=User, user=user)
    logger.info("Пользователь %s удалён (мягко)", user.pk)
    return user


def _ensure_customer(user: User) -> None:
    if user.is_staff or user.is_superuser:
        raise PermissionDenied("Действие доступно только для клиентов.")


def block_customer(user: User) -> User:
    _ensure_customer(user)
    if user.is_deleted:
        raise ValidationError("Пользователь удалён.")
    if user.is_active:
        user.is_active = False
        user.save(update_fields=["is_active"])
        revoke_all_refresh_tokens(user)
    return user


def unblock_customer(user: User) -> User:
    _ensure_customer(user)
    if user.is_deleted:
        raise ValidationError("Удалённого пользователя нельзя разблокировать.")
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])
    return user


def delete_customer(user: User) -> User:
    _ensure_customer(user)
    return soft_delete_user(user)


def authenticate_staff(*, email: str, password: str) -> User | None:
    """Вход в панель администратора. Не-staff получает тот же ответ, что и неверный пароль."""
    user = authenticate_user(email=email, password=password)
    if user is None or not user.is_staff:
        return None
    return user
