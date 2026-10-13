"""Заказы в панели администратора (сессия Django + CSRF, роль IsAdmin).
Смена статуса — только через orders.services.status (переходы проверяет state machine)."""

from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.mixins import AdminAPIMixin
from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services import status as status_service

from .serializers import (
    AdminOrderDetailSerializer,
    AdminOrderListSerializer,
    AdminTransitionSerializer,
)
from .views import order_detail_queryset

TAG = "admin-orders"


def _date_param(params, name):
    value = params.get(name)
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise ValidationError({name: ["Дата в формате ГГГГ-ММ-ДД."]})
    return parsed


@extend_schema(tags=[TAG])
class AdminOrderViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    def get_serializer_class(self):
        return AdminOrderListSerializer if self.action == "list" else AdminOrderDetailSerializer

    def get_queryset(self):
        if self.action != "list":
            return order_detail_queryset(Order.objects.all(), with_actors=True)

        queryset = (
            Order.objects.select_related("owner")
            .annotate(items_count=Sum("items__quantity"))
            .order_by("-created_at", "-id")
        )
        params = self.request.query_params
        for name in ("status", "payment_method", "delivery_method"):
            value = params.get(name)
            if value:
                queryset = queryset.filter(**{name: value})
        if params.get("unfinished") in ("1", "true"):
            queryset = queryset.unfinished()
        created_from = _date_param(params, "created_from")
        if created_from:
            queryset = queryset.filter(created_at__date__gte=created_from)
        created_to = _date_param(params, "created_to")
        if created_to:
            queryset = queryset.filter(created_at__date__lte=created_to)

        search = params.get("search", "").strip()
        if search:
            condition = (
                Q(number__icontains=search)
                | Q(owner__email__icontains=search)
                | Q(recipient_name__icontains=search)
            )
            digits = "".join(ch for ch in search if ch.isdigit())
            if len(digits) >= 4:
                condition |= Q(recipient_phone__contains=digits[-10:])
            queryset = queryset.filter(condition)
        return queryset

    @extend_schema(
        operation_id="admin_orders_list",
        parameters=[
            OpenApiParameter("status", str, enum=OrderStatus.values),
            OpenApiParameter("payment_method", str, enum=PaymentMethod.values),
            OpenApiParameter("delivery_method", str, enum=DeliveryMethod.values),
            OpenApiParameter("unfinished", bool, description="Только незавершённые заказы"),
            OpenApiParameter("created_from", str, description="Дата оформления от (ГГГГ-ММ-ДД)"),
            OpenApiParameter("created_to", str, description="Дата оформления до (ГГГГ-ММ-ДД)"),
            OpenApiParameter(
                "search", str, description="Номер заказа, email, имя или телефон получателя"
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(operation_id="admin_orders_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        operation_id="admin_orders_transition",
        request=AdminTransitionSerializer,
        responses=AdminOrderDetailSerializer,
        description=(
            "Перевести заказ в статус из allowed_transitions. Отмена возвращает остатки; "
            "«Оплачен» ставит только платёжная система."
        ),
    )
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()
        serializer = AdminTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        status_service.transition(
            order, serializer.validated_data["status"], by=ChangedBy.ADMIN, actor=request.user
        )
        fresh = self.get_queryset().get(pk=order.pk)
        return Response(self.get_serializer(fresh).data)
