"""Заказы клиента в мобильном приложении (JWT). Логика — orders.services."""

from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from orders.models import ChangedBy, Order, OrderItem, OrderStatusChange
from orders.services import checkout as checkout_service
from orders.services import status as status_service
from payments.models import Payment
from store.models import ProductImage

from .serializers import (
    BuyNowSerializer,
    CheckoutInputSerializer,
    CheckoutPreviewSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)

TAG = "orders"

IDEMPOTENCY_HEADER = OpenApiParameter(
    "Idempotency-Key",
    str,
    location=OpenApiParameter.HEADER,
    required=True,
    description=(
        "Уникальный ключ попытки оформления (8–64 символа: латиница, цифры, - и _). "
        "Повтор запроса с тем же ключом возвращает уже созданный заказ (200)."
    ),
)


class OrderCreateThrottle(UserRateThrottle):
    scope = "order_create"


def order_detail_queryset(queryset, *, with_actors: bool = False):
    changes = OrderStatusChange.objects.all()
    if with_actors:
        changes = changes.select_related("actor")
    return queryset.select_related("owner").prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related("product").prefetch_related(
                Prefetch("product__images", queryset=ProductImage.objects.order_by("position"))
            ),
        ),
        Prefetch("status_changes", queryset=changes),
        Prefetch("payments", queryset=Payment.objects.prefetch_related("refunds")),
    )


def customer_orders(user):
    return Order.objects.filter(owner=user)


@extend_schema(tags=[TAG])
class CheckoutPreviewView(APIView):
    @extend_schema(
        operation_id="orders_checkout_preview",
        responses=CheckoutPreviewSerializer,
        parameters=[
            OpenApiParameter("variant", int, description="«Купить сейчас»: id варианта"),
            OpenApiParameter("quantity", int, description="«Купить сейчас»: количество (1)"),
        ],
        description=(
            "Данные экрана оформления: корзина (тот же расчёт, что и в заказе), способы "
            "доставки со стоимостью, способы оплаты и получатель из последнего заказа. "
            "С variant — одна позиция «Купить сейчас» вместо корзины."
        ),
    )
    def get(self, request):
        buy_now = None
        if request.query_params.get("variant"):
            query = BuyNowSerializer(
                data={
                    "variant_id": request.query_params.get("variant"),
                    "quantity": request.query_params.get("quantity", 1),
                }
            )
            query.is_valid(raise_exception=True)
            buy_now = query.to_line()
        preview = checkout_service.preview(request.user, buy_now)
        return Response(CheckoutPreviewSerializer(preview, context={"request": request}).data)


@extend_schema(tags=[TAG])
class OrderListCreateView(generics.ListAPIView):
    serializer_class = OrderListSerializer

    def get_throttles(self):
        if self.request.method == "POST":
            return [OrderCreateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        # Meta.ordering не применяется к запросам с GROUP BY — порядок задаётся явно.
        return (
            customer_orders(self.request.user)
            .annotate(items_count=Sum("items__quantity"))
            .order_by("-created_at", "-id")
        )

    @extend_schema(operation_id="orders_list")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        operation_id="orders_create",
        parameters=[IDEMPOTENCY_HEADER],
        request=CheckoutInputSerializer,
        responses={
            201: OrderDetailSerializer,
            200: OpenApiResponse(OrderDetailSerializer, description="Повтор с тем же ключом"),
        },
        description=(
            "Оформить заказ из всей корзины или одну позицию buy_now (корзина не меняется). "
            "Ошибки корзины (empty_cart, cart_changed) и изменение суммы (total_changed) — "
            "400 с текстом для покупателя."
        ),
    )
    def post(self, request):
        serializer = CheckoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, created = checkout_service.checkout(
            request.user,
            serializer.to_input(),
            request.headers.get("Idempotency-Key", ""),
            buy_now=serializer.buy_now_line(),
        )
        order = order_detail_queryset(Order.objects.all()).get(pk=order.pk)
        data = OrderDetailSerializer(order, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@extend_schema(tags=[TAG])
class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    lookup_field = "number"

    def get_queryset(self):
        return order_detail_queryset(customer_orders(self.request.user))

    @extend_schema(operation_id="orders_retrieve")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class OrderCancelView(APIView):
    @extend_schema(
        operation_id="orders_cancel",
        request=None,
        responses=OrderDetailSerializer,
        description="Отмена до отправки заказа. Остатки возвращаются на склад.",
    )
    def post(self, request, number: str):
        order = get_object_or_404(customer_orders(request.user), number=number)
        status_service.cancel(order, by=ChangedBy.CUSTOMER, actor=request.user)
        order = order_detail_queryset(Order.objects.all()).get(pk=order.pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)
