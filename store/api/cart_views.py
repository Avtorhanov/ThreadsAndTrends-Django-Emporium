"""Корзина мобильного приложения.

Клиент (JWT) работает с корзиной на сервере. Гость хранит позиции на устройстве и получает
расчёт (цены, наличие, сумма) через публичный quote; после входа или регистрации
приложение переносит их на сервер через merge. Логика — store.services.cart.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.mixins import PublicAPIMixin
from core.api.throttles import IPRateThrottle
from store.services import cart as cart_service

from .cart_serializers import (
    CartAddSerializer,
    CartLinesInputSerializer,
    CartMergeResultSerializer,
    CartQuantitySerializer,
    CartSerializer,
)

TAG = "cart"


class CartQuoteThrottle(IPRateThrottle):
    scope = "cart_quote"


class CartResponseMixin:
    def cart_response(self, summary, status_code=status.HTTP_200_OK) -> Response:
        data = CartSerializer(summary, context={"request": self.request}).data
        return Response(data, status=status_code)


@extend_schema(tags=[TAG])
class CartView(CartResponseMixin, APIView):
    @extend_schema(operation_id="cart_retrieve", responses=CartSerializer)
    def get(self, request):
        return self.cart_response(cart_service.get_summary(request.user))


@extend_schema(tags=[TAG])
class CartItemsView(CartResponseMixin, APIView):
    @extend_schema(
        operation_id="cart_items_add",
        request=CartAddSerializer,
        responses={201: CartSerializer},
        description="Добавить вариант товара; если он уже в корзине — увеличить количество.",
    )
    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = cart_service.add(request.user, **serializer.validated_data)
        return self.cart_response(summary, status.HTTP_201_CREATED)


@extend_schema(tags=[TAG])
class CartItemView(CartResponseMixin, APIView):
    @extend_schema(
        operation_id="cart_items_set_quantity",
        request=CartQuantitySerializer,
        responses=CartSerializer,
    )
    def patch(self, request, pk: int):
        serializer = CartQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = cart_service.set_quantity(request.user, pk, serializer.validated_data["quantity"])
        return self.cart_response(summary)

    @extend_schema(operation_id="cart_items_remove", request=None, responses=CartSerializer)
    def delete(self, request, pk: int):
        return self.cart_response(cart_service.remove(request.user, pk))


@extend_schema(tags=[TAG])
class CartAckPricesView(CartResponseMixin, APIView):
    @extend_schema(
        operation_id="cart_ack_prices",
        request=None,
        responses=CartSerializer,
        description="Покупатель увидел изменившиеся цены: предупреждения снимаются.",
    )
    def post(self, request):
        return self.cart_response(cart_service.ack_prices(request.user))


@extend_schema(tags=[TAG])
class CartMergeView(APIView):
    @extend_schema(
        operation_id="cart_merge",
        request=CartLinesInputSerializer,
        responses=CartMergeResultSerializer,
        description=(
            "Перенос гостевой корзины с устройства после входа или регистрации. Количества "
            "складываются и ограничиваются доступным; недоступное пропускается (notices)."
        ),
    )
    def post(self, request):
        serializer = CartLinesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cart_service.merge(request.user, serializer.to_lines())
        return Response(CartMergeResultSerializer(result, context={"request": request}).data)


@extend_schema(tags=[TAG])
class CartQuoteView(PublicAPIMixin, CartResponseMixin, APIView):
    throttle_classes = [CartQuoteThrottle]

    @extend_schema(
        operation_id="cart_quote",
        request=CartLinesInputSerializer,
        responses=CartSerializer,
        description=(
            "Расчёт гостевой корзины по текущим ценам и наличию. Ничего не сохраняет; "
            "доступен без входа."
        ),
    )
    def post(self, request):
        serializer = CartLinesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self.cart_response(cart_service.quote(serializer.to_lines()))
