from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from store.services.cart import LineInput, LineStatus, MergeNoticeReason

from .serializers import absolute_url

# Защита от нелепых чисел во входных данных; реальный предел — остаток и CART_MAX_QUANTITY.
MAX_INPUT_QUANTITY = 1000


# --- Ответ ---


class CartProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()
    cover_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_url(self, product):
        cover = product.cover
        return absolute_url(self.context, cover.image) if cover else None


class CartLineSerializer(serializers.Serializer):
    id = serializers.IntegerField(
        allow_null=True, help_text="id позиции корзины; null — позиция гостевой корзины"
    )
    variant_id = serializers.IntegerField()
    product = CartProductSerializer(
        allow_null=True, help_text="null — вариант не существует (удалён из каталога)"
    )
    size = serializers.CharField(
        allow_null=True, help_text="Пустая строка — товар без размера; null — вариант не найден"
    )
    quantity = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=LineStatus.choices,
        help_text=(
            "ok — можно оформить; unavailable — товар снят с продажи; out_of_stock — нет в "
            "наличии; exceeds_stock — в корзине больше, чем max_quantity"
        ),
    )
    max_quantity = serializers.IntegerField(help_text="Сколько можно купить сейчас (0 — нельзя)")
    unit_price_kopecks = serializers.IntegerField(
        allow_null=True, help_text="Текущая цена товара, коп."
    )
    seen_price_kopecks = serializers.IntegerField(
        allow_null=True, help_text="Цена, которую покупатель видел последней, коп."
    )
    price_changed = serializers.BooleanField()
    line_total_kopecks = serializers.IntegerField(help_text="0, если позиция недоступна")


class CartSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True, source="lines")
    total_kopecks = serializers.IntegerField(
        help_text="Сумма доступных позиций по текущим ценам — сумма будущего заказа"
    )
    items_count = serializers.IntegerField(help_text="Всего единиц товара в корзине")
    can_checkout = serializers.BooleanField(
        help_text="Корзина не пуста и все позиции доступны в нужном количестве"
    )
    has_problems = serializers.BooleanField()
    has_price_changes = serializers.BooleanField()


class CartMergeNoticeSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=MergeNoticeReason.choices)


class CartMergeResultSerializer(serializers.Serializer):
    cart = CartSerializer(source="summary")
    notices = CartMergeNoticeSerializer(many=True)


# --- Запросы ---


class CartAddSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_INPUT_QUANTITY, default=1)


class CartQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_INPUT_QUANTITY)


class CartLineInputSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_INPUT_QUANTITY)
    seen_price_kopecks = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
        help_text="Цена, которую покупатель видел при добавлении, коп.",
    )


class CartLinesInputSerializer(serializers.Serializer):
    """Позиции гостевой корзины, хранящейся на устройстве."""

    items = CartLineInputSerializer(many=True, max_length=settings.CART_MAX_ITEMS)

    def to_lines(self) -> list[LineInput]:
        return [
            LineInput(
                variant_id=item["variant_id"],
                quantity=item["quantity"],
                seen_price_kopecks=item.get("seen_price_kopecks"),
            )
            for item in self.validated_data["items"]
        ]
