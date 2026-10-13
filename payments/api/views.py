"""Оплата заказа из мобильного приложения (JWT) и webhook провайдера. Логика — payments.services."""

import ipaddress
import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle, UserRateThrottle
from rest_framework.views import APIView

from core.api.mixins import PublicAPIMixin
from orders.api.serializers import OrderDetailSerializer
from orders.api.views import customer_orders, order_detail_queryset
from orders.models import Order
from payments import services
from payments.providers import ProviderError

from .serializers import PaymentStartInputSerializer, PaymentStartSerializer

logger = logging.getLogger(__name__)

TAG = "orders"


class PaymentServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Платёжный сервис временно недоступен. Попробуйте через минуту."
    default_code = "payment_unavailable"


class PaymentStartThrottle(UserRateThrottle):
    scope = "payment_start"


class PaymentRefreshThrottle(UserRateThrottle):
    scope = "payment_refresh"


UNAVAILABLE = OpenApiResponse(description="Провайдер временно недоступен — повторить позже")


@extend_schema(tags=[TAG])
class OrderPayView(APIView):
    throttle_classes = [PaymentStartThrottle]

    @extend_schema(
        operation_id="orders_pay",
        request=PaymentStartInputSerializer,
        responses={200: PaymentStartSerializer, 503: UNAVAILABLE},
        description=(
            "Ссылка на страницу оплаты онлайн-заказа в статусе «Ожидает оплаты». Повторный "
            "вызов возвращает ту же попытку оплаты, пока она не завершилась. Статус заказа "
            "меняется только по подтверждению провайдера."
        ),
    )
    def post(self, request, number: str):
        order = get_object_or_404(customer_orders(request.user), number=number)
        serializer = PaymentStartInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = services.start_payment(
                order, return_url=serializer.validated_data["return_url"]
            )
        except services.PaymentUnavailable as exc:
            raise PaymentServiceUnavailable() from exc
        data = {"confirmation_url": payment.confirmation_url, "payment_status": payment.status}
        return Response(PaymentStartSerializer(data).data)


@extend_schema(tags=[TAG])
class OrderPaymentRefreshView(APIView):
    throttle_classes = [PaymentRefreshThrottle]

    @extend_schema(
        operation_id="orders_pay_refresh",
        request=None,
        responses={200: OrderDetailSerializer, 503: UNAVAILABLE},
        description=(
            "Сверить оплату с провайдером (после возврата со страницы оплаты) и вернуть заказ."
        ),
    )
    def post(self, request, number: str):
        order = get_object_or_404(customer_orders(request.user), number=number)
        try:
            services.sync_order_payments(order)
        except services.PaymentUnavailable as exc:
            raise PaymentServiceUnavailable() from exc
        fresh = order_detail_queryset(Order.objects.all()).get(pk=order.pk)
        return Response(OrderDetailSerializer(fresh, context={"request": request}).data)


def webhook_ip_allowed(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(
        address in ipaddress.ip_network(network, strict=False)
        for network in settings.YOOKASSA_WEBHOOK_IPS
    )


@extend_schema(exclude=True)
class YooKassaWebhookView(PublicAPIMixin, APIView):
    """Уведомления ЮKassa. Подлинность: IP из списка ЮKassa (YOOKASSA_WEBHOOK_IPS, за nginx —
    NUM_PROXIES=1) и обязательный перезапрос объекта по API — содержимое уведомления не
    применяется. 503 — провайдер недоступен, ЮKassa повторит уведомление."""

    throttle_classes: list = []

    def post(self, request):
        ip = BaseThrottle().get_ident(request)
        if not webhook_ip_allowed(ip):
            logger.warning("Webhook ЮKassa с недоверенного адреса %s отклонён", ip)
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not isinstance(request.data, dict):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            services.handle_notification(request.data)
        except ProviderError as exc:
            if exc.transient:
                logger.warning("Webhook ЮKassa: провайдер недоступен, ждём повтор: %s", exc)
                return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
            logger.error("Webhook ЮKassa: объект не получен: %s", exc)
        return Response({})
