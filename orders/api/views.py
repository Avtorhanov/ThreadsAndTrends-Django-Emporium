"""Заказы клиента в мобильном приложении (JWT). Логика — orders.services."""

import hashlib

from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from core.api.mixins import PublicAPIMixin
from core.api.throttles import IPRateThrottle
from orders.models import ChangedBy, Order, OrderItem, OrderStatusChange
from orders.services import checkout as checkout_service
from orders.services import guest as guest_service
from orders.services import status as status_service
from payments.models import Payment
from store.models import ProductImage

from .serializers import (
    BuyNowSerializer,
    CheckoutInputSerializer,
    CheckoutPreviewSerializer,
    GuestCheckoutInputSerializer,
    GuestClaimInputSerializer,
    GuestClaimSerializer,
    GuestOrderCreatedSerializer,
    GuestPreviewInputSerializer,
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

    @extend_schema(
        operation_id="orders_retrieve",
        description="Открытие заказа покупателем гасит отметку «есть новости» (status_unseen).",
    )
    def get(self, request, *args, **kwargs):
        order = self.get_object()
        status_service.mark_seen(order)
        return Response(self.get_serializer(order).data)


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


# --- Заказ без аккаунта ---

ORDER_TOKEN_HEADER = OpenApiParameter(
    "X-Order-Token",
    str,
    location=OpenApiParameter.HEADER,
    required=True,
    description="Секрет доступа к гостевому заказу (access_token при оформлении).",
)


def _request_phone(request) -> str | None:
    try:
        return checkout_service.normalize_phone(str(request.data.get("recipient_phone", "")))
    except ValidationError:
        return None  # опечатка в номере не тратит попытки: ошибку вернёт сервис


class _GuestCreateIPThrottle(IPRateThrottle):
    def get_cache_key(self, request, view):
        return super().get_cache_key(request, view) if _request_phone(request) else None


class GuestCreateHourThrottle(_GuestCreateIPThrottle):
    scope = "order_create_guest"


class GuestCreateDayThrottle(_GuestCreateIPThrottle):
    scope = "order_create_guest_day"


class GuestCreatePhoneThrottle(SimpleRateThrottle):
    scope = "order_create_guest_phone"

    def get_cache_key(self, request, view):
        phone = _request_phone(request)
        if phone is None:
            return None
        ident = hashlib.sha256(phone.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class GuestPreviewThrottle(IPRateThrottle):
    scope = "cart_quote"


class GuestAccessThrottle(IPRateThrottle):
    scope = "order_guest_access"


def _guest_order_or_404(request) -> Order:
    token = request.headers.get("X-Order-Token", "")
    return get_object_or_404(guest_service.by_token(token))


def _guest_detail_response(request, order: Order) -> Response:
    order = order_detail_queryset(Order.objects.all()).get(pk=order.pk)
    return Response(OrderDetailSerializer(order, context={"request": request}).data)


@extend_schema(tags=[TAG])
class GuestPreviewView(PublicAPIMixin, APIView):
    throttle_classes = [GuestPreviewThrottle]

    @extend_schema(
        operation_id="orders_guest_preview",
        request=GuestPreviewInputSerializer,
        responses=CheckoutPreviewSerializer,
        description="Экран оформления без аккаунта: позиции с устройства, доставка и оплата.",
    )
    def post(self, request):
        serializer = GuestPreviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview = checkout_service.guest_preview(serializer.to_lines())
        return Response(CheckoutPreviewSerializer(preview, context={"request": request}).data)


@extend_schema(tags=[TAG])
class GuestCheckoutView(PublicAPIMixin, APIView):
    throttle_classes = [GuestCreateHourThrottle, GuestCreateDayThrottle, GuestCreatePhoneThrottle]

    @extend_schema(
        operation_id="orders_guest_create",
        parameters=[IDEMPOTENCY_HEADER],
        request=GuestCheckoutInputSerializer,
        responses={
            201: GuestOrderCreatedSerializer,
            200: OpenApiResponse(GuestOrderCreatedSerializer, description="Повтор с тем же ключом"),
        },
        description=(
            "Оформить заказ без аккаунта, только «по согласованию». Ключ идемпотентности — "
            "32–64 символа; повтор с другим телефоном — 400."
        ),
    )
    def post(self, request):
        serializer = GuestCheckoutInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = checkout_service.guest_checkout(
            serializer.to_input(),
            request.headers.get("Idempotency-Key", ""),
            serializer.to_lines(),
            consent=serializer.validated_data["consent"],
        )
        order = order_detail_queryset(Order.objects.all()).get(pk=result.order.pk)
        data = GuestOrderCreatedSerializer(
            {"order": order, "access_token": result.token}, context={"request": request}
        ).data
        return Response(
            data, status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        )


@extend_schema(tags=[TAG])
class GuestOrderView(PublicAPIMixin, APIView):
    throttle_classes = [GuestAccessThrottle]

    @extend_schema(
        operation_id="orders_guest_retrieve",
        parameters=[ORDER_TOKEN_HEADER],
        responses=OrderDetailSerializer,
        description="Гостевой заказ по токену. Неверный или истёкший токен — 404.",
    )
    def get(self, request):
        return _guest_detail_response(request, _guest_order_or_404(request))


@extend_schema(tags=[TAG])
class GuestOrderCancelView(PublicAPIMixin, APIView):
    throttle_classes = [GuestAccessThrottle]

    @extend_schema(
        operation_id="orders_guest_cancel",
        parameters=[ORDER_TOKEN_HEADER],
        request=None,
        responses=OrderDetailSerializer,
        description="Отмена гостевого заказа до отправки. Остатки возвращаются на склад.",
    )
    def post(self, request):
        order = _guest_order_or_404(request)
        status_service.cancel(order, by=ChangedBy.CUSTOMER)
        return _guest_detail_response(request, order)


@extend_schema(tags=[TAG])
class GuestClaimView(APIView):
    throttle_classes = [GuestAccessThrottle]

    @extend_schema(
        operation_id="orders_guest_claim",
        request=GuestClaimInputSerializer,
        responses=GuestClaimSerializer,
        description="Привязать гостевые заказы к аккаунту по токенам; ссылки перестают работать.",
    )
    def post(self, request):
        serializer = GuestClaimInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claimed = guest_service.claim(request.user, serializer.validated_data["tokens"])
        return Response(GuestClaimSerializer({"numbers": [o.number for o in claimed]}).data)
