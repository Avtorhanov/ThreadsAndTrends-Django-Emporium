from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from core.choices import AgreementChannel
from orders.models import ChangedBy, DeliveryMethod, Order, OrderStatus, PaymentMethod
from orders.services import agreement
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


class GuestLineSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=99)


class GuestPreviewInputSerializer(serializers.Serializer):
    lines = GuestLineSerializer(many=True, allow_empty=False)

    def to_lines(self) -> list[LineInput]:
        return [LineInput(r["variant_id"], r["quantity"]) for r in self.validated_data["lines"]]


class GuestCheckoutInputSerializer(CheckoutInputSerializer):
    """Оформление без аккаунта: позиции с устройства вместо корзины на сервере."""

    buy_now = None
    lines = GuestLineSerializer(many=True, allow_empty=False)
    consent = serializers.BooleanField(help_text="Согласие на обработку персональных данных")

    def to_input(self) -> CheckoutInput:
        skip = ("lines", "consent")
        return CheckoutInput(**{k: v for k, v in self.validated_data.items() if k not in skip})

    def to_lines(self) -> list[LineInput]:
        return [LineInput(r["variant_id"], r["quantity"]) for r in self.validated_data["lines"]]


class GuestClaimInputSerializer(serializers.Serializer):
    tokens = serializers.ListField(
        child=serializers.CharField(max_length=64), allow_empty=False, max_length=20
    )


class GuestClaimSerializer(serializers.Serializer):
    numbers = serializers.ListField(
        child=serializers.CharField(), help_text="Номера заказов, привязанных к аккаунту"
    )


# --- Заказ ---


class OrderItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product_slug = serializers.CharField(source="product.slug")
    product_name = serializers.CharField()
    size = serializers.CharField(help_text="Пусто — товар без размера")
    color_name = serializers.CharField(help_text="Цвет на момент заказа; пусто — без цвета")
    sku = serializers.CharField()
    status_name = serializers.CharField(
        help_text="Статус товара на момент заказа («Под заказ»); пусто — без статуса"
    )
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
    comment = serializers.CharField(help_text="Комментарий магазина для клиента; пусто — нет")
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
            "status_unseen",
            "created_at",
        ]
        read_only_fields = fields
        extra_kwargs = {
            "status_unseen": {"help_text": "Магазин сменил статус, заказ ещё не открыт"}
        }


class AgreementLinkSerializer(serializers.Serializer):
    """Связь с продавцом для заказа «по согласованию», пока он ждёт подтверждения."""

    kind = serializers.ChoiceField(choices=AgreementChannel.choices)
    title = serializers.CharField(help_text="Подпись канала: «WhatsApp» или своя")
    url = serializers.CharField(help_text="https://wa.me/…?text=…, https://t.me/…, tel:+7…")
    handle = serializers.CharField(help_text="Номер или имя канала для показа")
    message = serializers.CharField(help_text="Текст продавцу: номер заказа, товары, сумма")
    prefilled = serializers.BooleanField(
        help_text="Текст уже в ссылке (WhatsApp); иначе — скопировать и вставить в чат"
    )
    deadline = serializers.DateTimeField(help_text="Не подтверждённый к этому времени — отменится")


def base_url(context) -> str:
    """Адрес сайта для ссылок на товары в сообщении продавцу."""
    if settings.SITE_URL:
        return settings.SITE_URL
    request = context.get("request")
    return request.build_absolute_uri("/").rstrip("/") if request else ""


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
    agreement = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "number",
            "status",
            "status_display",
            "payment_method",
            "payment_method_display",
            "agreement_channel",
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
            "agreement",
        ]
        read_only_fields = fields
        extra_kwargs = {
            "agreement_channel": {"help_text": "Канал согласования; пусто — другой способ оплаты"}
        }

    @extend_schema_field(AgreementLinkSerializer(allow_null=True))
    def get_agreement(self, order):
        found = agreement.link(order, base_url(self.context))
        return AgreementLinkSerializer(found).data if found else None

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


class GuestOrderCreatedSerializer(serializers.Serializer):
    order = OrderDetailSerializer()
    access_token = serializers.CharField(
        help_text="Секрет доступа к заказу: заголовок X-Order-Token"
    )


# --- Панель администратора ---


class AdminOrderCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_deleted = serializers.BooleanField()


class AdminOrderListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display")
    customer = AdminOrderCustomerSerializer(
        source="owner", allow_null=True, help_text="null — гостевой заказ"
    )
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
    notified = serializers.BooleanField(help_text="Клиенту отправлено письмо")

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_actor_email(self, change):
        return change.actor.email if change.actor else None


class AdminTransitionOptionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    label = serializers.CharField()


class AdminOrderDetailSerializer(OrderDetailSerializer):
    customer = AdminOrderCustomerSerializer(
        source="owner", allow_null=True, help_text="null — гостевой заказ"
    )
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
                if f
                not in ("can_cancel", "can_pay", "payment_status", "refund_status", "agreement")
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


class AdminBulkTransitionSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,
        help_text="id заказов (до 100)",
    )
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
        help_text="Пояснение для клиента: история заказа и письмо",
    )
    notify = serializers.BooleanField(
        required=False, default=True, help_text="Отправить клиентам письма о смене статуса"
    )


class AdminBulkSkippedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    number = serializers.CharField()
    reason = serializers.CharField()


class AdminBulkTransitionResultSerializer(serializers.Serializer):
    updated = serializers.ListField(child=serializers.IntegerField(), help_text="id переведённых")
    skipped = AdminBulkSkippedSerializer(many=True)


class AdminTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    comment = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
        help_text="Пояснение для клиента: история заказа и письмо",
    )
    notify = serializers.BooleanField(
        required=False, default=True, help_text="Отправить клиенту письмо о смене статуса"
    )
