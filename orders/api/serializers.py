from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services.checkout import CheckoutInput
from orders.services.status import allowed_transitions, can_cancel
from payments import services as payment_services
from payments.api.serializers import AdminPaymentSerializer
from payments.models import PaymentStatus, RefundStatus
from store.api.cart_serializers import CartSerializer
from store.api.serializers import absolute_url
from store.services.cart import LineInput

# --- Экран оформления ---


class DeliveryOptionSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    title = serializers.CharField()
    cost_kopecks = serializers.IntegerField(help_text="Стоимость для текущей корзины, коп.")
    address = serializers.CharField(help_text="Адрес пункта самовывоза; пусто для курьера")


class RecipientDefaultsSerializer(serializers.Serializer):
    recipient_name = serializers.CharField()
    recipient_phone = serializers.CharField()
    delivery_address = serializers.CharField()


class CheckoutPreviewSerializer(serializers.Serializer):
    cart = CartSerializer()
    delivery_options = DeliveryOptionSerializer(many=True)
    payment_methods = serializers.ListField(
        child=serializers.ChoiceField(choices=PaymentMethod.choices)
    )
    free_delivery_from_kopecks = serializers.IntegerField(
        help_text="Курьерская доставка бесплатна от этой суммы товаров, коп."
    )
    defaults = RecipientDefaultsSerializer(help_text="Данные получателя из последнего заказа")


class BuyNowSerializer(serializers.Serializer):
    """«Купить сейчас»: одна позиция мимо корзины (корзина не меняется)."""

    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=99, default=1)

    def to_line(self) -> LineInput:
        return LineInput(self.validated_data["variant_id"], self.validated_data["quantity"])


class CheckoutInputSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    recipient_name = serializers.CharField(max_length=150)
    recipient_phone = serializers.CharField(max_length=32, help_text="Российский номер")
    delivery_address = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
        help_text="Обязателен для курьера; для самовывоза игнорируется",
    )
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    expected_total_kopecks = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Итог, который видел покупатель; если сумма изменилась — 400 (total_changed)",
    )
    buy_now = BuyNowSerializer(
        required=False,
        allow_null=True,
        help_text="«Купить сейчас»: оформить только эту позицию, корзина не меняется",
    )

    def to_input(self) -> CheckoutInput:
        data = {k: v for k, v in self.validated_data.items() if k != "buy_now"}
        return CheckoutInput(**data)

    def buy_now_line(self) -> LineInput | None:
        raw = self.validated_data.get("buy_now")
        return LineInput(raw["variant_id"], raw["quantity"]) if raw else None


# --- Заказ ---


class OrderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_slug = serializers.CharField(source="product.slug")
    product_name = serializers.CharField()
    size = serializers.CharField(help_text="Пусто — товар без размера")
    sku = serializers.CharField()
    price_kopecks = serializers.IntegerField(help_text="Цена на момент заказа, коп.")
    quantity = serializers.IntegerField()
    line_total_kopecks = serializers.IntegerField()
    cover_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_url(self, item):
        cover = item.product.cover
        return absolute_url(self.context, cover.image) if cover else None


class OrderStatusChangeSerializer(serializers.Serializer):
    from_status = serializers.ChoiceField(
        choices=OrderStatus.choices, allow_blank=True, help_text="Пусто — оформление заказа"
    )
    to_status = serializers.ChoiceField(choices=OrderStatus.choices)
    to_status_display = serializers.CharField(source="get_to_status_display")
    changed_by = serializers.ChoiceField(choices=ChangedBy.choices)
    created_at = serializers.DateTimeField()


class OrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display")
    items_count = serializers.IntegerField(help_text="Всего единиц товара")

    class Meta:
        model = Order
        fields = [
            "number",
            "status",
            "status_display",
            "payment_method",
            "delivery_method",
            "total_kopecks",
            "items_count",
            "created_at",
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display")
    payment_method_display = serializers.CharField(source="get_payment_method_display")
    delivery_method_display = serializers.CharField(source="get_delivery_method_display")
    items = OrderItemSerializer(many=True)
    status_history = OrderStatusChangeSerializer(many=True, source="status_changes")
    can_cancel = serializers.SerializerMethodField()
    can_pay = serializers.SerializerMethodField()
    pay_until = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    refund_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "number",
            "status",
            "status_display",
            "payment_method",
            "payment_method_display",
            "delivery_method",
            "delivery_method_display",
            "items_total_kopecks",
            "delivery_kopecks",
            "total_kopecks",
            "recipient_name",
            "recipient_phone",
            "delivery_address",
            "comment",
            "created_at",
            "items",
            "status_history",
            "can_cancel",
            "can_pay",
            "pay_until",
            "payment_status",
            "refund_status",
        ]
        read_only_fields = fields

    def get_can_cancel(self, order) -> bool:
        return can_cancel(order, ChangedBy.CUSTOMER)

    def _payment(self, order) -> payment_services.PaymentSummary:
        # Один расчёт на заказ (платежи и возвраты — из prefetch order_detail_queryset).
        cache = self.context.setdefault("_payment_summary", {})
        if order.pk not in cache:
            cache[order.pk] = payment_services.summary(order)
        return cache[order.pk]

    def get_can_pay(self, order) -> bool:
        return self._payment(order).can_pay

    @extend_schema_field(
        serializers.DateTimeField(
            allow_null=True, help_text="Срок оплаты онлайн-заказа; потом заказ отменяется"
        )
    )
    def get_pay_until(self, order):
        deadline = self._payment(order).pay_until
        return serializers.DateTimeField().to_representation(deadline) if deadline else None

    @extend_schema_field(
        serializers.ChoiceField(
            choices=PaymentStatus.choices,
            allow_null=True,
            help_text="Статус последней попытки онлайн-оплаты; null — не было",
        )
    )
    def get_payment_status(self, order):
        return self._payment(order).payment_status

    @extend_schema_field(
        serializers.ChoiceField(
            choices=RefundStatus.choices,
            allow_null=True,
            help_text="Статус последнего возврата денег; null — возврата не было",
        )
    )
    def get_refund_status(self, order):
        return self._payment(order).refund_status


# --- Панель администратора ---


class AdminOrderCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_deleted = serializers.BooleanField()


class AdminOrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display")
    customer = AdminOrderCustomerSerializer(source="owner")
    items_count = serializers.IntegerField()

    class Meta:
        model = Order
        fields = [
            "id",
            "number",
            "status",
            "status_display",
            "customer",
            "recipient_name",
            "recipient_phone",
            "payment_method",
            "delivery_method",
            "total_kopecks",
            "items_count",
            "created_at",
        ]
        read_only_fields = fields


class AdminOrderStatusChangeSerializer(OrderStatusChangeSerializer):
    actor_email = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_actor_email(self, change):
        return change.actor.email if change.actor else None


class AdminTransitionOptionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    label = serializers.CharField()


class AdminOrderDetailSerializer(OrderDetailSerializer):
    customer = AdminOrderCustomerSerializer(source="owner")
    status_history = AdminOrderStatusChangeSerializer(many=True, source="status_changes")
    allowed_transitions = serializers.SerializerMethodField()
    payments = AdminPaymentSerializer(many=True, help_text="Попытки онлайн-оплаты и возвраты")
    can_retry_refund = serializers.SerializerMethodField()

    class Meta(OrderDetailSerializer.Meta):
        fields = [
            "id",
            "customer",
            *[
                f
                for f in OrderDetailSerializer.Meta.fields
                if f not in ("can_cancel", "can_pay", "payment_status", "refund_status")
            ],
            "updated_at",
            "allowed_transitions",
            "payments",
            "can_retry_refund",
        ]
        read_only_fields = fields

    def get_can_retry_refund(self, order) -> bool:
        return payment_services.refund_retry_payment(order) is not None

    @extend_schema_field(AdminTransitionOptionSerializer(many=True))
    def get_allowed_transitions(self, order):
        return [
            {"status": status, "label": OrderStatus(status).label}
            for status in allowed_transitions(order, ChangedBy.ADMIN)
        ]


class AdminTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
