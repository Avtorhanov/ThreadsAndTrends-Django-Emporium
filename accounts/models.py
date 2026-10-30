import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


def normalize_email(value: str) -> str:
    """Email хранится и сравнивается в нижнем регистре целиком."""
    return (value or "").strip().lower()


class UserQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def customers(self):
        return self.filter(is_staff=False, is_superuser=False)


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    def _create_user(self, email, password, **extra_fields):
        email = normalize_email(email)
        if not email:
            raise ValueError("Email обязателен")
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # None → непригодный пароль
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Суперпользователь должен иметь is_staff=True и is_superuser=True")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        # Вход по email без учёта регистра.
        return self.get(email=normalize_email(email))


def avatar_path(instance, filename):
    # Фото профиля всегда перекодируется в WebP (accounts.services.set_avatar): имя — UUID.
    return f"avatars/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.webp"


class User(AbstractUser):
    """Клиент (is_staff=False) или Администратор (is_staff=True, единственный продавец).

    Удаление мягкое: deleted_at + анонимизация (accounts.services.soft_delete_user).
    """

    username = None
    email = models.EmailField("Email", unique=True)
    deleted_at = models.DateTimeField("Удалён", null=True, blank=True, db_index=True)
    # db_default: строки, вставленные в обход модели (миграции данных, старые версии кода),
    # получают пустое значение, а не NULL.
    avatar = models.ImageField(
        "Фото профиля", upload_to=avatar_path, blank=True, default="", db_default=""
    )

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-date_joined"]
        indexes = [models.Index(fields=["is_staff", "date_joined"], name="user_staff_joined_idx")]

    def __str__(self):
        return self.email

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def clean(self):
        super().clean()
        self.email = normalize_email(self.email)

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        super().save(*args, **kwargs)


class PasswordResetCode(models.Model):
    """Одноразовый код сброса пароля. Хранится только HMAC кода."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
        verbose_name="Пользователь",
    )
    code_hash = models.CharField("HMAC кода", max_length=64)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    expires_at = models.DateTimeField("Действует до", db_index=True)
    attempts = models.PositiveSmallIntegerField("Неудачных попыток", default=0)
    used_at = models.DateTimeField("Использован/аннулирован", null=True, blank=True)

    class Meta:
        verbose_name = "Код сброса пароля"
        verbose_name_plural = "Коды сброса пароля"
        indexes = [models.Index(fields=["user", "-created_at"], name="reset_code_user_created_idx")]

    def __str__(self):
        return f"Код сброса для {self.user_id} от {self.created_at:%Y-%m-%d %H:%M}"


class StaffAccess(models.Model):
    """Права сотрудника панели по разделам: {раздел: none | view | edit}.

    Есть только у приглашённых сотрудников. Владелец (суперпользователь) и администратор без
    этой записи (созданный до появления сотрудников) — без ограничений.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="staff_access",
        verbose_name="Сотрудник",
    )
    permissions = models.JSONField("Права по разделам", default=dict)
    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Пригласил",
    )
    created_at = models.DateTimeField("Приглашён", auto_now_add=True)
    updated_at = models.DateTimeField("Изменён", auto_now=True)

    class Meta:
        verbose_name = "Права сотрудника"
        verbose_name_plural = "Права сотрудников"

    def __str__(self):
        return f"Права {self.user_id}"
