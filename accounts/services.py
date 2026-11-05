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
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from core.tasks import send_email

from .models import EmailChangeCode, PasswordResetCode, User, normalize_email
from .signals import account_deleted, account_deleting

logger = logging.getLogger(__name__)

AVATAR_SIZE = 320  # px, квадрат: в профиле — до 96 px, запас на экраны 3x
AVATAR_QUALITY = 82

RESET_CODE_TTL = timedelta(minutes=15)
RESET_CODE_MAX_ATTEMPTS = 5
RESET_CODE_RESEND_COOLDOWN = timedelta(seconds=60)
RESET_CODES_PER_HOUR = 5
INVALID_RESET_CODE = "Неверный или просроченный код."

EMAIL_CODE_TTL = timedelta(minutes=15)
EMAIL_CODE_MAX_ATTEMPTS = 5
EMAIL_CODE_RESEND_COOLDOWN = timedelta(seconds=60)
EMAIL_CODES_PER_HOUR = 5
EMAIL_TAKEN = "Этот email уже занят другим аккаунтом."


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


def update_password(user: User, *, old_password: str, new_password: str) -> None:
    """Смена пароля со старым паролем: приложение на всех устройствах выходит (refresh-токены
    отозваны), сессии сайта и панели с прежним паролем перестают действовать. Текущую сессию
    вызывающий сохраняет сам (update_session_auth_hash)."""
    if not user.check_password(old_password):
        raise ValidationError({"old_password": "Неверный текущий пароль."})
    _validate_new_password(new_password, user, field="new_password")
    with transaction.atomic():
        # Пароль и отзыв refresh-токенов — вместе: без живых токенов со старым паролем.
        user.set_password(new_password)
        user.save(update_fields=["password"])
        revoke_all_refresh_tokens(user)


def change_password(user: User, *, old_password: str, new_password: str) -> dict[str, str]:
    """Смена пароля из приложения: остальные устройства разлогиниваются, текущему —
    новая пара токенов."""
    update_password(user, old_password=old_password, new_password=new_password)
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


# --- Смена email: код на новый адрес, уведомление на прежний ---


def _hash_email_code(user_id: int, new_email: str, code: str) -> str:
    # Новый адрес входит в HMAC: код подтверждает именно его.
    return salted_hmac("accounts.email_change", f"{user_id}:{new_email}:{code}").hexdigest()


def _email_taken(email: str, user: User) -> bool:
    return User.objects.filter(email=email).exclude(pk=user.pk).exists()


def mask_email(email: str) -> str:
    """ivan.petrov@mail.ru → i***v@mail.ru: в письме на прежний адрес новый не виден целиком."""
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def pending_email_change(user: User) -> EmailChangeCode | None:
    """Действующий запрос смены email (для формы ввода кода)."""
    return (
        EmailChangeCode.objects.filter(
            user=user, used_at__isnull=True, expires_at__gt=timezone.now()
        )
        .order_by("-created_at")
        .first()
    )


def request_email_change(user: User, *, new_email: str, password: str) -> EmailChangeCode:
    """Шаг 1: проверить пароль и новый адрес, отправить на него код из 6 цифр.

    Пароль обязателен: открытая на чужом устройстве сессия не позволяет увести аккаунт."""
    if not user.check_password(password):
        raise ValidationError({"password": "Неверный пароль."})
    email = normalize_email(new_email)
    try:
        validate_email(email)
    except ValidationError as exc:
        raise ValidationError({"new_email": "Введите корректный email."}) from exc
    if email == user.email:
        raise ValidationError({"new_email": "Это ваш текущий email."})

    code = f"{secrets.randbelow(10**6):06d}"
    with transaction.atomic():
        # Блокировка пользователя: параллельные запросы не проходят лимиты одновременно.
        User.objects.select_for_update().only("pk").get(pk=user.pk)
        now = timezone.now()
        recent = EmailChangeCode.objects.filter(user=user, created_at__gte=now - timedelta(hours=1))
        if recent.count() >= EMAIL_CODES_PER_HOUR:
            raise ValidationError("Слишком много запросов. Попробуйте через час.", code="throttled")
        if recent.filter(created_at__gte=now - EMAIL_CODE_RESEND_COOLDOWN).exists():
            raise ValidationError(
                "Код уже отправлен. Повторно — не раньше чем через минуту.", code="throttled"
            )
        # После лимитов: проверка «адрес занят» не быстрее, чем 5 запросов в час.
        if _email_taken(email, user):
            raise ValidationError({"new_email": EMAIL_TAKEN})
        # Действует только последний запрос.
        EmailChangeCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
        record = EmailChangeCode.objects.create(
            user=user,
            new_email=email,
            code_hash=_hash_email_code(user.pk, email, code),
            expires_at=now + EMAIL_CODE_TTL,
        )
        body = render_to_string(
            "accounts/email/email_change_code.txt",
            {"user": user, "code": code, "ttl_minutes": int(EMAIL_CODE_TTL.total_seconds() // 60)},
        )
        transaction.on_commit(
            lambda: send_email.enqueue("DiDi-shop: код для смены email", body, [email])
        )
    return record


def cancel_email_change(user: User) -> None:
    EmailChangeCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())


def confirm_email_change(user: User, *, code: str) -> User:
    """Шаг 2: код с нового адреса → email аккаунта меняется, на прежний уходит уведомление.
    Сессии и токены остаются: пароль не менялся."""
    now = timezone.now()
    old_email = user.email
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        record = (
            EmailChangeCode.objects.select_for_update()
            .filter(user=locked, used_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        if record is None or record.attempts >= EMAIL_CODE_MAX_ATTEMPTS:
            status = "invalid"
        elif not constant_time_compare(
            _hash_email_code(locked.pk, record.new_email, code.strip()), record.code_hash
        ):
            # Счётчик сохраняется: исключение бросаем после выхода из транзакции.
            status = "invalid"
            record.attempts += 1
            record.save(update_fields=["attempts"])
        elif _email_taken(record.new_email, locked):
            # Адрес заняли, пока шёл код.
            status = "taken"
            record.used_at = now
            record.save(update_fields=["used_at"])
        else:
            status = "ok"
            record.used_at = now
            record.save(update_fields=["used_at"])
            locked.email = record.new_email
            try:
                with transaction.atomic():
                    locked.save(update_fields=["email"])
            except IntegrityError:
                status = "taken"
            else:
                # Коды сброса пароля ушли на прежний адрес — после смены email они не действуют.
                PasswordResetCode.objects.filter(user=locked, used_at__isnull=True).update(
                    used_at=now
                )
                body = render_to_string(
                    "accounts/email/email_changed.txt",
                    {"user": locked, "masked_email": mask_email(locked.email)},
                )
                transaction.on_commit(
                    lambda: send_email.enqueue("DiDi-shop: email изменён", body, [old_email])
                )

    if status == "invalid":
        raise ValidationError({"code": INVALID_RESET_CODE})
    if status == "taken":
        raise ValidationError({"code": EMAIL_TAKEN})
    logger.info("Email изменён по коду для пользователя %s", locked.pk)
    user.email = locked.email
    return locked


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
