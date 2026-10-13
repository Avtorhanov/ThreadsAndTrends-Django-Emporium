from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services.checkout import CheckoutInput
from orders.services.status import allowed_transitions, can_cancel
from store.api.cart_serializers import CartSerializer
from store.api.serializers import absolute_url

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

    def to_input(self) -> CheckoutInput:
        return CheckoutInput(**self.validated_data)


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
        ]
        read_only_fields = fields

    def get_can_cancel(self, order) -> bool:
        return can_cancel(order, ChangedBy.CUSTOMER)


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

    class Meta(OrderDetailSerializer.Meta):
        fields = [
            "id",
            "customer",
            *[f for f in OrderDetailSerializer.Meta.fields if f != "can_cancel"],
            "updated_at",
            "allowed_transitions",
        ]
        read_only_fields = fields

    @extend_schema_field(AdminTransitionOptionSerializer(many=True))
    def get_allowed_transitions(self, order):
        return [
            {"status": status, "label": OrderStatus(status).label}
            for status in allowed_transitions(order, ChangedBy.ADMIN)
        ]


class AdminTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
