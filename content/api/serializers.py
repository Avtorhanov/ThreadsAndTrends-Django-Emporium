from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from content import home, look, shop
from content.contacts import ContactKind
from content.models import (
    Article,
    ArticleImage,
    Block,
    BlockArea,
    BlockKind,
    CollectionSource,
    HomeBlock,
    HomeBlockKind,
    ShopSettings,
)
from content.services import MAX_BODY_LENGTH
from store.api.serializers import CatalogProductSerializer, absolute_url
from store.models import Category

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


# --- Главная из блоков ---


def _image_url(context, image) -> str | None:
    """Копия 960 px, если готова, иначе оригинал (баннер на телефоне уже не нужен крупнее)."""
    if image is None:
        return None
    sources = image.sources
    url = next((u for u, width in sources if width == 960), sources[-1][0])
    request = context.get("request")
    return request.build_absolute_uri(url) if request else url


class HomeCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    slug = serializers.CharField()
    name = serializers.CharField()


class HomeBlockSerializer(serializers.Serializer):
    """Блок опубликованной главной с данными для показа."""

    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=HomeBlockKind.choices)
    title = serializers.CharField()
    text = serializers.CharField(help_text="Баннер — описание; текст — абзацы через пустую строку")
    color = serializers.CharField(help_text="Фон баннера #RRGGBB; у других блоков пусто")
    ink = serializers.CharField(help_text="Цвет текста на фоне баннера")
    image_url = serializers.SerializerMethodField()
    category = HomeCategorySerializer(
        allow_null=True, help_text="Баннер — переход в категорию; подборка — «Все»"
    )
    products = CatalogProductSerializer(many=True)
    categories = HomeCategorySerializer(many=True, help_text="Лента категорий: корневые")

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image_url(self, block):
        return _image_url(self.context, block.image)


class HomeSerializer(serializers.Serializer):
    blocks = HomeBlockSerializer(many=True)


class AdminHomeBlockSerializer(serializers.ModelSerializer):
    ink = serializers.SerializerMethodField()
    product_ids = serializers.ListField(
        child=serializers.IntegerField(), read_only=True, help_text="Ручная подборка по порядку"
    )
    image_url = serializers.SerializerMethodField()
    preview_products = serializers.SerializerMethodField(
        help_text="Товары подборки, как их увидит покупатель"
    )

    class Meta:
        model = HomeBlock
        fields = [
            "id",
            "kind",
            "position",
            "is_visible",
            "title",
            "text",
            "color",
            "ink",
            "image_url",
            "category",
            "source",
            "product_ids",
            "preview_products",
        ]
        read_only_fields = fields

    def get_ink(self, block) -> str:
        return home.ink_for(block.color)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image_url(self, block):
        return _image_url(self.context, block.image)

    @extend_schema_field(CatalogProductSerializer(many=True))
    def get_preview_products(self, block):
        if block.kind != HomeBlockKind.COLLECTION:
            return []
        resolved = home.resolve([home.snapshot_of(block)], keep_empty=True)[0]
        return CatalogProductSerializer(resolved.products, many=True, context=self.context).data


class AdminHomeSerializer(serializers.Serializer):
    blocks = AdminHomeBlockSerializer(many=True)
    has_changes = serializers.BooleanField(help_text="Есть неопубликованные правки")
    published_at = serializers.DateTimeField(allow_null=True)


class AdminHomeBlockCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=HomeBlockKind.choices)


class AdminHomeBlockUpdateSerializer(serializers.Serializer):
    is_visible = serializers.BooleanField(required=False)
    title = serializers.CharField(max_length=home.TITLE_MAX, required=False, allow_blank=True)
    text = serializers.CharField(
        max_length=home.TEXT_MAX, required=False, allow_blank=True, trim_whitespace=False
    )
    color = serializers.CharField(max_length=7, required=False, allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )
    source = serializers.ChoiceField(choices=CollectionSource.choices, required=False)
    product_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        max_length=home.MAX_MANUAL_PRODUCTS,
        required=False,
    )


class AdminHomeImageUploadSerializer(serializers.Serializer):
    image = serializers.FileField(help_text="JPEG, PNG или WebP, до 5 МБ")


class AdminHomeReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Все id блоков в новом порядке"
    )


# --- Тема для покупателей ---


class ThemePaletteSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=look.PALETTE_CHOICES)
    name = serializers.CharField()
    group = serializers.ChoiceField(choices=look.PALETTE_GROUP_CHOICES)
    note = serializers.CharField()
    accent = serializers.CharField(help_text="Цвет акцента — для образца")
    brand = serializers.CharField(help_text="Фирменный цвет — для образца")
    bg_light = serializers.CharField(source="bg.light", help_text="Фон светлой темы")
    bg_dark = serializers.CharField(source="bg.dark", help_text="Фон тёмной темы")


class ThemeAccentSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    color = serializers.CharField()
    on = serializers.CharField(help_text="Цвет текста на акценте")


class ShopThemeSerializer(serializers.Serializer):
    """Что может выбрать покупатель и что видит новый посетитель."""

    palettes = ThemePaletteSerializer(many=True, help_text="Доступные палитры по порядку")
    accents = ThemeAccentSerializer(many=True, help_text="Акценты палитры «Своя»")
    default_palette = serializers.ChoiceField(choices=look.PALETTE_CHOICES)
    default_mode = serializers.ChoiceField(choices=look.MODE_CHOICES)
    default_radius = serializers.ChoiceField(choices=look.RADIUS_CHOICES)
    nav_style = serializers.ChoiceField(
        choices=look.NAV_CHOICES, help_text="Вид нижнего меню витрины на телефоне"
    )


class AdminThemeSerializer(ShopThemeSerializer):
    enabled = serializers.ListField(
        child=serializers.ChoiceField(choices=look.PALETTE_CHOICES),
        help_text="Ключи палитр, доступных покупателям",
    )


class AdminThemeWriteSerializer(serializers.Serializer):
    palettes = serializers.ListField(
        child=serializers.ChoiceField(choices=look.PALETTE_CHOICES),
        help_text="Ключи палитр, доступных покупателям",
    )
    default_palette = serializers.ChoiceField(choices=look.PALETTE_CHOICES)
    default_mode = serializers.ChoiceField(choices=look.MODE_CHOICES)
    default_radius = serializers.ChoiceField(choices=look.RADIUS_CHOICES)
    nav_style = serializers.ChoiceField(
        choices=look.NAV_CHOICES,
        required=False,
        help_text="Вид нижнего меню витрины; не передан — прежний",
    )
