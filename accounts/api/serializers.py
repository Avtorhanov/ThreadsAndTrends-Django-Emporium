from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.models import User

# --- Мобильный клиент ---


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access-токен (заголовок Authorization: Bearer)")
    refresh = serializers.CharField(help_text="JWT refresh-токен; одноразовый, ротируется")


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "date_joined"]
        read_only_fields = ["id", "email", "date_joined"]


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


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Код — 6 цифр."})
    new_password = serializers.CharField(trim_whitespace=False, max_length=128)


# --- Панель администратора ---


class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_superuser"]
        read_only_fields = fields


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
