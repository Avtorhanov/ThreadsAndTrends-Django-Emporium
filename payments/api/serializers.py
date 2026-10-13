from rest_framework import serializers

from payments.models import PaymentStatus, RefundReason, RefundStatus


class PaymentStartInputSerializer(serializers.Serializer):
    return_url = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        default="",
        help_text=(
            "Адрес возврата в приложение после оплаты (deep link). Пусто — "
            "адрес по умолчанию didishop://orders/<номер>"
        ),
    )


class PaymentStartSerializer(serializers.Serializer):
    confirmation_url = serializers.URLField(help_text="Страница оплаты провайдера")
    payment_status = serializers.ChoiceField(choices=PaymentStatus.choices)


class AdminRefundSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount_kopecks = serializers.IntegerField()
    status = serializers.ChoiceField(choices=RefundStatus.choices)
    status_display = serializers.CharField(source="get_status_display")
    reason = serializers.ChoiceField(choices=RefundReason.choices)
    reason_display = serializers.CharField(source="get_reason_display")
    provider_refund_id = serializers.CharField(allow_null=True)
    cancellation_reason = serializers.CharField()
    created_at = serializers.DateTimeField()


class AdminPaymentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount_kopecks = serializers.IntegerField()
    status = serializers.ChoiceField(choices=PaymentStatus.choices)
    status_display = serializers.CharField(source="get_status_display")
    provider_payment_id = serializers.CharField(allow_null=True)
    cancellation_reason = serializers.CharField()
    created_at = serializers.DateTimeField()
    paid_at = serializers.DateTimeField(allow_null=True)
    refunds = AdminRefundSerializer(many=True)
