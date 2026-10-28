from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from content import shop
from content.contacts import ContactKind
from content.models import Article, ArticleImage, Block, BlockArea, BlockKind, ShopSettings
from content.services import MAX_BODY_LENGTH
from store.api.serializers import absolute_url

# --- Публичное чтение (приложение) ---


class ArticleImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ArticleImage
        fields = ["id", "url", "width", "height"]
        read_only_fields = fields

    def get_url(self, obj) -> str:
        return absolute_url(self.context, obj.image) or ""


class ArticleSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = ["id", "slug", "title", "excerpt", "published_at", "cover_url"]
        read_only_fields = fields

    def get_cover_url(self, obj) -> str | None:
        cover = obj.cover
        return absolute_url(self.context, cover.image) if cover else None


class ArticleDetailSerializer(ArticleSerializer):
    paragraphs = serializers.ListField(
        child=serializers.CharField(), read_only=True, help_text="Абзацы текста (без HTML)"
    )
    images = ArticleImageSerializer(many=True, read_only=True)

    class Meta(ArticleSerializer.Meta):
        fields = [*ArticleSerializer.Meta.fields, "paragraphs", "images"]
        read_only_fields = fields


class ContactSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ContactKind.CHOICES)
    title = serializers.CharField()
    url = serializers.CharField(help_text="https://wa.me/…, https://t.me/…, tel:…, mailto:…")
    handle = serializers.CharField(help_text="Как показать: номер, @имя, адрес")
    note = serializers.CharField()


# --- Панель администратора ---


class AdminArticleImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ArticleImage
        fields = ["id", "url", "position"]
        read_only_fields = fields

    def get_url(self, obj) -> str:
        return absolute_url(self.context, obj.image) or ""


class AdminArticleSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    images_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "slug",
            "title",
            "excerpt",
            "is_published",
            "published_at",
            "created_at",
            "updated_at",
            "deleted_at",
            "cover_url",
            "images_count",
        ]
        read_only_fields = fields

    def get_cover_url(self, obj) -> str | None:
        cover = obj.cover
        return absolute_url(self.context, cover.image) if cover else None


class AdminArticleDetailSerializer(AdminArticleSerializer):
    images = AdminArticleImageSerializer(many=True, read_only=True)

    class Meta(AdminArticleSerializer.Meta):
        fields = [*AdminArticleSerializer.Meta.fields, "body", "images"]
        read_only_fields = fields


class AdminArticleWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    excerpt = serializers.CharField(max_length=300, allow_blank=True, required=False)
    body = serializers.CharField(
        max_length=MAX_BODY_LENGTH,
        allow_blank=True,
        required=False,
        trim_whitespace=False,
        help_text="Абзацы через пустую строку, без HTML",
    )
    is_published = serializers.BooleanField(required=False)


class AdminArticleImageUploadSerializer(serializers.Serializer):
    image = serializers.FileField(help_text="JPEG, PNG или WebP, до 5 МБ")


class AdminArticleImageReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Все id фото статьи в новом порядке"
    )


# --- Тексты и блоки витрины (правка на сайте) ---


class AdminSiteTextSerializer(serializers.Serializer):
    key = serializers.CharField(read_only=True)
    value = serializers.CharField(
        allow_blank=True,
        max_length=2000,
        trim_whitespace=False,
        help_text="Обычный текст; пусто — текст скрыт на сайте",
    )


class AdminBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ["id", "area", "kind", "title", "value", "note", "icon", "position"]
        read_only_fields = ["id", "position"]


class AdminBlockUpdateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=BlockKind.choices, required=False)
    title = serializers.CharField(max_length=80, required=False, allow_blank=True)
    value = serializers.CharField(max_length=300, required=False)
    note = serializers.CharField(max_length=160, required=False, allow_blank=True)
    icon = serializers.CharField(max_length=20, required=False, allow_blank=True)


class AdminBlockAreaSerializer(serializers.Serializer):
    area = serializers.ChoiceField(choices=BlockArea.choices)


class AdminBlockReorderSerializer(serializers.Serializer):
    area = serializers.ChoiceField(choices=BlockArea.choices)
    ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Все id блоков раздела в новом порядке"
    )


# --- Настройки магазина (панель → «Настройки») ---


class AdminShopDefaultsSerializer(serializers.Serializer):
    """Значения из .env — действуют, пока поле в панели пустое."""

    delivery_courier_kopecks = serializers.IntegerField()
    delivery_free_from_kopecks = serializers.IntegerField()
    pickup_address = serializers.CharField()
    unpaid_timeout_minutes = serializers.IntegerField()
    seller_name = serializers.CharField()
    seller_inn = serializers.CharField()
    seller_ogrn = serializers.CharField()
    seller_address = serializers.CharField()
    seller_phone = serializers.CharField()
    seller_email = serializers.CharField()


class AdminShopSettingsSerializer(serializers.ModelSerializer):
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)
    online_payment_available = serializers.SerializerMethodField(
        help_text="Онлайн-оплата подключена на сервере (ключи ЮKassa в .env)"
    )
    defaults = serializers.SerializerMethodField()

    class Meta:
        model = ShopSettings
        fields = [*shop.FIELDS, "updated_at", "online_payment_available", "defaults"]
        read_only_fields = fields

    def get_online_payment_available(self, obj) -> bool:
        return shop.online_payment_available()

    @extend_schema_field(AdminShopDefaultsSerializer)
    def get_defaults(self, obj):
        return AdminShopDefaultsSerializer(shop.env_defaults()).data


class AdminShopSettingsWriteSerializer(serializers.Serializer):
    """Все поля разом; пустая строка или null — значение из .env."""

    delivery_courier_kopecks = serializers.IntegerField(min_value=0, allow_null=True)
    delivery_free_from_kopecks = serializers.IntegerField(min_value=0, allow_null=True)
    pickup_enabled = serializers.BooleanField()
    pickup_address = serializers.CharField(max_length=300, allow_blank=True)
    cash_on_delivery_enabled = serializers.BooleanField()
    unpaid_timeout_minutes = serializers.IntegerField(min_value=1, allow_null=True)
    seller_name = serializers.CharField(max_length=200, allow_blank=True)
    seller_inn = serializers.CharField(max_length=20, allow_blank=True)
    seller_ogrn = serializers.CharField(max_length=20, allow_blank=True)
    seller_address = serializers.CharField(max_length=300, allow_blank=True)
    seller_phone = serializers.CharField(max_length=30, allow_blank=True)
    seller_email = serializers.CharField(max_length=254, allow_blank=True)
