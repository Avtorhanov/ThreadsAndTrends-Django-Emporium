"""Сводка для главной страницы панели администратора: что требует внимания сегодня.

Оборот — сумма заказов, которые не отменены и не ждут онлайн-оплаты (принятые к исполнению),
по дате оформления. Это оборот магазина, а не поступившие деньги: заказ с оплатой при получении
учитывается сразу после оформления."""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.mixins import AdminAPIMixin
from orders.models import Order, OrderStatus
from store.models import ProductVariant

LOW_STOCK_LIMIT = 8
EXCLUDED_FROM_TURNOVER = (OrderStatus.CANCELLED, OrderStatus.AWAITING_PAYMENT)


class AdminSummaryPeriodSerializer(serializers.Serializer):
    """Заказы за период по дате оформления."""

    orders = serializers.IntegerField(help_text="Оформлено заказов, кроме отменённых")
    turnover_kopecks = serializers.IntegerField(
        help_text="Оборот без отменённых и неоплаченных, коп."
    )


class AdminLowStockVariantSerializer(serializers.Serializer):
    """Вариант активного товара с остатком не выше порога."""

    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    size = serializers.CharField(help_text="Пусто — товар без размеров")
    sku = serializers.CharField()
    stock = serializers.IntegerField()


class AdminSummarySerializer(serializers.Serializer):
    """Сводка панели; периоды — от полуночи по времени магазина."""

    # today — с полуночи, last_7_days и last_30_days — включая сегодня (TIME_ZONE).

    generated_at = serializers.DateTimeField()
    today = AdminSummaryPeriodSerializer()
    last_7_days = AdminSummaryPeriodSerializer()
    last_30_days = AdminSummaryPeriodSerializer()
    awaiting_payment = serializers.IntegerField(help_text="Ждут онлайн-оплаты")
    to_assemble = serializers.IntegerField(help_text="Приняты или оплачены — нужно собрать")
    to_deliver = serializers.IntegerField(help_text="Собраны, отправлены или ждут в пункте выдачи")
    low_stock_threshold = serializers.IntegerField()
    low_stock_count = serializers.IntegerField(help_text="Всего вариантов с малым остатком")
    low_stock = AdminLowStockVariantSerializer(many=True)


def _period(since) -> dict:
    row = (
        Order.objects.filter(created_at__gte=since)
        .exclude(status=OrderStatus.CANCELLED)
        .aggregate(
            orders=Count("id"),
            turnover=Sum("total_kopecks", filter=~Q(status__in=EXCLUDED_FROM_TURNOVER)),
        )
    )
    return {"orders": row["orders"], "turnover_kopecks": row["turnover"] or 0}


def build_summary(now=None) -> dict:
    now = now or timezone.now()
    local_today = timezone.localtime(now).date()
    midnight = timezone.make_aware(datetime.combine(local_today, time.min))

    by_status = dict(
        Order.objects.unfinished().values_list("status").annotate(n=Count("id")).order_by()
    )

    def count(*statuses) -> int:
        return sum(by_status.get(status, 0) for status in statuses)

    threshold = settings.ADMIN_LOW_STOCK_THRESHOLD
    low = (
        ProductVariant.objects.filter(
            stock__lte=threshold,
            product__deleted_at__isnull=True,
            product__is_active=True,
        )
        .select_related("product")
        .order_by("stock", "product__name", "position", "id")
    )
    return {
        "generated_at": now,
        "today": _period(midnight),
        "last_7_days": _period(midnight - timedelta(days=6)),
        "last_30_days": _period(midnight - timedelta(days=29)),
        "awaiting_payment": count(OrderStatus.AWAITING_PAYMENT),
        "to_assemble": count(OrderStatus.CONFIRMED, OrderStatus.PAID),
        "to_deliver": count(
            OrderStatus.ASSEMBLED, OrderStatus.SHIPPED, OrderStatus.READY_FOR_PICKUP
        ),
        "low_stock_threshold": threshold,
        "low_stock_count": low.count(),
        "low_stock": [
            {
                "product_id": variant.product_id,
                "product_name": variant.product.name,
                "size": variant.size,
                "sku": variant.sku,
                "stock": variant.stock,
            }
            for variant in low[:LOW_STOCK_LIMIT]
        ],
    }


class AdminSummaryView(AdminAPIMixin, APIView):
    section = "summary"

    @extend_schema(
        operation_id="admin_summary",
        description="Сводка для главной страницы панели.",
        tags=["admin-summary"],
        responses=AdminSummarySerializer,
    )
    def get(self, request):
        return Response(AdminSummarySerializer(build_summary()).data)
