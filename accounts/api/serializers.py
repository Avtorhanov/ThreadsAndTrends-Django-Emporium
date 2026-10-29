from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts import staff
from accounts.models import User

# --- Мобильный клиент ---


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access-токен (заголовок Authorization: Bearer)")
    refresh = serializers.CharField(help_text="JWT refresh-токен; одноразовый, ротируется")


class ProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(help_text="Фото профиля (WebP 320×320) или null")

    class Meta:
        model = User
        # is_staff — в приложении у сотрудника есть вход в панель управления.
        fields = ["id", "email", "first_name", "last_name", "date_joined", "is_staff", "avatar_url"]
        read_only_fields = ["id", "email", "date_joined", "is_staff", "avatar_url"]

    def get_avatar_url(self, user) -> str | None:
        if not user.avatar:
            return None
        request = self.context.get("request")
        url = user.avatar.url
        return request.build_absolute_uri(url) if request else url


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField(help_text="JPEG, PNG или WebP до 5 МБ")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class AuthResultSerializer(TokenPairSerializer):
    user = ProfileSerializer()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, max_length=128)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, max_length=128)
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False, max_length=128)


class PasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Код — 6 цифр."})
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)


# --- Панель администратора ---


LEVEL_CHOICES = staff.LEVEL_CHOICES


class StaffPermissionsSerializer(serializers.Serializer):
    """Уровень доступа по каждому разделу панели."""

    summary = serializers.ChoiceField(choices=LEVEL_CHOICES)
    orders = serializers.ChoiceField(choices=LEVEL_CHOICES)
    products = serializers.ChoiceField(choices=LEVEL_CHOICES)
    categories = serializers.ChoiceField(choices=LEVEL_CHOICES)
    articles = serializers.ChoiceField(choices=LEVEL_CHOICES)
    storefront = serializers.ChoiceField(choices=LEVEL_CHOICES)
    customers = serializers.ChoiceField(choices=LEVEL_CHOICES)
    settings = serializers.ChoiceField(choices=LEVEL_CHOICES, help_text="Только владелец")
    staff = serializers.ChoiceField(choices=LEVEL_CHOICES, help_text="Только владелец")


class StaffPermissionsInputSerializer(serializers.Serializer):
    """Права сотрудника: не переданный раздел — нет доступа. Владельческие разделы не выдаются."""

    summary = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    orders = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    products = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    categories = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    articles = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    storefront = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)
    customers = serializers.ChoiceField(choices=LEVEL_CHOICES, required=False)


class StaffUserSerializer(serializers.ModelSerializer):
    is_owner = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "is_superuser",
            "is_owner",
            "permissions",
        ]
        read_only_fields = fields

    def get_is_owner(self, user) -> bool:
        return staff.is_owner(user)

    @extend_schema_field(StaffPermissionsSerializer)
    def get_permissions(self, user):
        return staff.access_for(user).as_dict()


class StaffMemberSerializer(StaffUserSerializer):
    invited = serializers.SerializerMethodField(help_text="Приглашён, но ещё не задал пароль")

    class Meta(StaffUserSerializer.Meta):
        fields = [
            *StaffUserSerializer.Meta.fields,
            "is_active",
            "invited",
            "last_login",
            "date_joined",
        ]
        read_only_fields = fields

    def get_invited(self, user) -> bool:
        return not user.has_usable_password()


class StaffInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    permissions = StaffPermissionsInputSerializer()


class StaffUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    is_active = serializers.BooleanField(
        required=False, help_text="false — отключить: вход закрыт, сессии завершены"
    )
    permissions = StaffPermissionsInputSerializer(required=False)


class CustomerStatus:
    ACTIVE = "active"
    BLOCKED = "blocked"
    DELETED = "deleted"
    CHOICES = [ACTIVE, BLOCKED, DELETED]


class CustomerSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "status",
            "date_joined",
            "last_login",
            "deleted_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=CustomerStatus.CHOICES))
    def get_status(self, obj: User) -> str:
        if obj.is_deleted:
            return CustomerStatus.DELETED
        return CustomerStatus.ACTIVE if obj.is_active else CustomerStatus.BLOCKED
