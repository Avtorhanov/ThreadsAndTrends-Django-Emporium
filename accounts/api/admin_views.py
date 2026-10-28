"""API панели администратора (React SPA).

Аутентификация — сессия Django в httpOnly-cookie + CSRF-токен в заголовке X-CSRFToken.
JWT мобильного клиента сюда не принимается: украденный токен приложения не даёт доступа
к управлению магазином.
"""

from django.contrib.auth import login, logout
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import services, staff
from accounts.models import User
from core.api.mixins import AdminAPIMixin

from .serializers import (
    CustomerSerializer,
    CustomerStatus,
    LoginSerializer,
    StaffInviteSerializer,
    StaffMemberSerializer,
    StaffUpdateSerializer,
    StaffUserSerializer,
)
from .throttles import LoginEmailThrottle, LoginIPThrottle

TAG = "admin"


@extend_schema(tags=[TAG])
class AdminCsrfView(AdminAPIMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={204: None},
        operation_id="admin_csrf",
        description="Выставляет cookie csrftoken для последующих POST-запросов панели.",
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
@method_decorator(csrf_protect, name="dispatch")
class AdminLoginView(AdminAPIMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginIPThrottle, LoginEmailThrottle]

    @extend_schema(
        request=LoginSerializer, responses={200: StaffUserSerializer}, operation_id="admin_login"
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.authenticate_staff(**serializer.validated_data)
        if user is None:
            raise AuthenticationFailed("Неверный email или пароль.")
        login(request._request, user)
        return Response(StaffUserSerializer(user).data)


@extend_schema(tags=[TAG])
class AdminLogoutView(AdminAPIMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None}, operation_id="admin_logout")
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
class AdminMeView(AdminAPIMixin, APIView):
    @extend_schema(responses={200: StaffUserSerializer}, operation_id="admin_me")
    def get(self, request):
        return Response(StaffUserSerializer(request.user).data)


@extend_schema(tags=[TAG])
class CustomerViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Клиенты магазина. Администраторы в выборку не попадают и через неё не изменяются."""

    section = "customers"

    serializer_class = CustomerSerializer

    def get_queryset(self):
        queryset = User.objects.customers().order_by("-date_joined", "-id")
        if self.action != "list":
            return queryset

        params = self.request.query_params
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        customer_status = params.get("status")
        if customer_status == CustomerStatus.ACTIVE:
            queryset = queryset.filter(deleted_at__isnull=True, is_active=True)
        elif customer_status == CustomerStatus.BLOCKED:
            queryset = queryset.filter(deleted_at__isnull=True, is_active=False)
        elif customer_status == CustomerStatus.DELETED:
            queryset = queryset.filter(deleted_at__isnull=False)
        return queryset

    @extend_schema(
        operation_id="admin_customers_list",
        parameters=[
            OpenApiParameter("search", str, description="Поиск по email, имени и фамилии"),
            OpenApiParameter("status", str, enum=CustomerStatus.CHOICES),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(operation_id="admin_customers_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(request=None, responses={200: CustomerSerializer})
    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        user = services.block_customer(self.get_object())
        return Response(CustomerSerializer(user).data)

    @extend_schema(request=None, responses={200: CustomerSerializer})
    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        user = services.unblock_customer(self.get_object())
        return Response(CustomerSerializer(user).data)

    @extend_schema(
        request=None,
        responses={200: CustomerSerializer},
        description="Мягкое удаление с анонимизацией, как при удалении клиентом.",
    )
    @action(detail=True, methods=["post"], url_path="delete")
    def soft_delete(self, request, pk=None):
        user = services.delete_customer(self.get_object())
        return Response(CustomerSerializer(user).data)


@extend_schema(tags=[TAG])
class StaffViewSet(AdminAPIMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """Сотрудники панели: приглашение по email, права по разделам, отключение. Только владелец."""

    section = "staff"
    serializer_class = StaffMemberSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return staff.staff_queryset().order_by("-is_superuser", "date_joined", "id")

    @extend_schema(operation_id="admin_staff_list")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        operation_id="admin_staff_create",
        request=StaffInviteSerializer,
        responses={201: StaffMemberSerializer},
        description="Пригласить: письмо с кодом, по которому сотрудник сам задаёт пароль.",
    )
    def create(self, request):
        serializer = StaffInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = staff.invite(request.user, **serializer.validated_data)
        fresh = self.get_queryset().get(pk=user.pk)
        return Response(StaffMemberSerializer(fresh).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="admin_staff_partial_update",
        request=StaffUpdateSerializer,
        responses=StaffMemberSerializer,
    )
    def partial_update(self, request, pk=None):
        serializer = StaffUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = staff.update(request.user, self.get_object(), **serializer.validated_data)
        return Response(StaffMemberSerializer(user).data)

    @extend_schema(
        operation_id="admin_staff_resend",
        request=None,
        responses={204: None},
        description="Отправить приглашение ещё раз (новый код; прежний перестаёт действовать).",
    )
    @action(detail=True, methods=["post"])
    def resend(self, request, pk=None):
        staff.resend_invite(request.user, self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
