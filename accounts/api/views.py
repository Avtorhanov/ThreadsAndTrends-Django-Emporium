"""API аутентификации мобильного клиента (JWT)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from accounts import services

from .serializers import (
    AuthResultSerializer,
    ChangePasswordSerializer,
    DeleteAccountSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
)
from .throttles import (
    LoginEmailThrottle,
    LoginIPThrottle,
    PasswordResetConfirmEmailThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetThrottle,
    RegisterThrottle,
    SensitiveActionThrottle,
)

TAG = "auth"


# Эндпоинты без аутентификации: токен не нужен и не проверяется.
class PublicAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        # Без аутентификаторов DRF превратил бы 401 (неверный пароль/токен) в 403.
        return 'Bearer realm="api"'


@extend_schema(tags=[TAG])
class RegisterView(PublicAPIView):
    throttle_classes = [RegisterThrottle]

    @extend_schema(
        request=RegisterSerializer, responses={201: AuthResultSerializer}, operation_id="register"
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_customer(**serializer.validated_data)
        tokens = services.issue_tokens(user)
        return Response(
            AuthResultSerializer({**tokens, "user": user}).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=[TAG])
class LoginView(PublicAPIView):
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    @extend_schema(
        request=LoginSerializer,
        responses={200: AuthResultSerializer, 401: OpenApiResponse(description="Неверные данные")},
        operation_id="login",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.authenticate_user(**serializer.validated_data)
        if user is None:
            raise AuthenticationFailed("Неверный email или пароль.")
        tokens = services.issue_tokens(user)
        return Response(AuthResultSerializer({**tokens, "user": user}).data)


@extend_schema(tags=[TAG])
class RefreshView(PublicAPIView):
    @extend_schema(
        request=RefreshSerializer,
        responses={200: TokenPairSerializer, 401: OpenApiResponse(description="Токен отозван")},
        operation_id="refresh_tokens",
        description="Ротация: старый refresh попадает в чёрный список, выдаётся новая пара.",
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        return Response(TokenPairSerializer(serializer.validated_data).data)


@extend_schema(tags=[TAG])
class LogoutView(PublicAPIView):
    @extend_schema(
        request=RefreshSerializer,
        responses={204: None},
        operation_id="logout",
        description="Отзыв refresh-токена текущего устройства. Работает и с истёкшим access.",
    )
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.logout(None, serializer.validated_data["refresh"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProfileSerializer}, operation_id="get_profile")
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    @extend_schema(
        request=ProfileSerializer, responses={200: ProfileSerializer}, operation_id="update_profile"
    )
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = services.update_profile(request.user, **serializer.validated_data)
        return Response(ProfileSerializer(user).data)


@extend_schema(tags=[TAG])
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveActionThrottle]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: TokenPairSerializer},
        operation_id="change_password",
        description="Остальные устройства разлогиниваются; текущему выдаётся новая пара токенов.",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = services.change_password(request.user, **serializer.validated_data)
        return Response(TokenPairSerializer(tokens).data)


@extend_schema(tags=[TAG])
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveActionThrottle]

    @extend_schema(
        request=DeleteAccountSerializer,
        responses={204: None},
        operation_id="delete_account",
        description="Мягкое удаление с анонимизацией. Требуется текущий пароль.",
    )
    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.delete_own_account(request.user, **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
class PasswordResetRequestView(PublicAPIView):
    throttle_classes = [PasswordResetThrottle]

    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={202: None},
        operation_id="request_password_reset",
        description="Всегда 202: ответ не раскрывает, зарегистрирован ли email.",
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=[TAG])
class PasswordResetConfirmView(PublicAPIView):
    throttle_classes = [PasswordResetConfirmThrottle, PasswordResetConfirmEmailThrottle]

    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={200: TokenPairSerializer},
        operation_id="confirm_password_reset",
        description="Новый пароль по коду из письма; все прежние сессии завершаются.",
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = services.confirm_password_reset(**serializer.validated_data)
        return Response(TokenPairSerializer(tokens).data)
