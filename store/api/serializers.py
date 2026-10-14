from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from store.models import Category, Product, ProductImage, ProductVariant
from store.services.catalog import MAX_PRICE_KOPECKS
from store.services.storefront import Sort


def absolute_url(context, file) -> str | None:
    if not file:
        return None
    request = context.get("request")
    url = file.url
    return request.build_absolute_uri(url) if request else url


# --- Публичный каталог (мобильное приложение) ---


class CatalogCategoryShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name"]
        read_only_fields = fields


class CatalogCategoryTreeSerializer(serializers.ModelSerializer):
    children = CatalogCategoryShortSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "slug", "name", "children"]
        read_only_fields = fields


class CatalogImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url"]
        read_only_fields = fields

    def get_url(self, obj) -> str:
        return absolute_url(self.context, obj.image) or ""


class CatalogVariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ["id", "size", "in_stock"]
        read_only_fields = fields

    def get_in_stock(self, obj) -> bool:
        return obj.stock > 0


class CatalogProductSerializer(serializers.ModelSerializer):
    category = CatalogCategoryShortSerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name",
            "price_kopecks",
            "compare_at_kopecks",
            "in_stock",
            "cover_url",
            "category",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_url(self, obj):
        cover = obj.cover
        return absolute_url(self.context, cover.image) if cover else None


class ProductListQuerySerializer(serializers.Serializer):
    """Параметры ленты товаров. Цены — копейки."""

    q = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Поиск по названию и описанию (по началу слов, русская морфология). "
        "Показывает только товары в наличии.",
    )
    category = serializers.SlugField(
        required=False, allow_blank=True, help_text="Slug категории (с подкатегориями)"
    )
    price_min = serializers.IntegerField(
        required=False, min_value=0, max_value=MAX_PRICE_KOPECKS, help_text="Цена от, коп."
    )
    price_max = serializers.IntegerField(
        required=False, min_value=0, max_value=MAX_PRICE_KOPECKS, help_text="Цена до, коп."
    )
    in_stock = serializers.BooleanField(required=False, default=False, help_text="Только в наличии")
    sort = serializers.ChoiceField(
        choices=Sort.CHOICES,
        required=False,
        allow_blank=True,
        help_text="По умолчанию: с поиском — relevance, без — new.",
    )

    def validate(self, attrs):
        low, high = attrs.get("price_min"), attrs.get("price_max")
        if low is not None and high is not None and low > high:
            raise serializers.ValidationError({"price_max": ["Меньше, чем «цена от»."]})
        return attrs


class CatalogProductDetailSerializer(CatalogProductSerializer):
    images = CatalogImageSerializer(many=True, read_only=True)
    variants = CatalogVariantSerializer(many=True, read_only=True)

    class Meta(CatalogProductSerializer.Meta):
        fields = [*CatalogProductSerializer.Meta.fields, "description", "images", "variants"]
        read_only_fields = fields


# --- Панель администратора ---


class AdminCategorySerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False
    )
    slug = serializers.SlugField(
        max_length=120,
        required=False,
        allow_blank=True,
        help_text="Пусто — сгенерировать из названия (только при создании).",
    )
    products_count = serializers.IntegerField(
        read_only=True, help_text="Товаров без учёта удалённых"
    )
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "position",
            "is_active",
            "products_count",
            "children_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "products_count", "children_count", "created_at", "updated_at"]


class AdminVariantSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Пусто — сгенерировать (DD-<id товара>-<размер>).",
    )
    position = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = ProductVariant
        fields = ["id", "size", "sku", "stock", "position"]
        read_only_fields = ["id"]
        # Уникальность размера и артикула проверяет сервис (с учётом мягкого удаления).
        validators = []
        extra_kwargs = {"size": {"required": False}, "stock": {"required": False}}


class AdminImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "url", "position"]
        read_only_fields = fields

    def get_url(self, obj) -> str:
        return absolute_url(self.context, obj.image) or ""


class AdminImageUploadSerializer(serializers.Serializer):
    image = serializers.FileField(help_text="JPEG, PNG или WebP, до 5 МБ")


class AdminImageReorderSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="Все id изображений товара в новом порядке"
    )


class AdminProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.__str__", read_only=True)
    total_stock = serializers.IntegerField(read_only=True, help_text="Сумма остатков вариантов")
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_name",
            "price_kopecks",
            "compare_at_kopecks",
            "is_active",
            "deleted_at",
            "total_stock",
            "cover_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cover_url(self, obj):
        cover = obj.cover
        return absolute_url(self.context, cover.image) if cover else None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["total_stock"] = data["total_stock"] or 0
        return data


class AdminProductDetailSerializer(AdminProductSerializer):
    variants = AdminVariantSerializer(many=True, read_only=True)
    images = AdminImageSerializer(many=True, read_only=True)

    class Meta(AdminProductSerializer.Meta):
        fields = [*AdminProductSerializer.Meta.fields, "description", "variants", "images"]
        read_only_fields = fields


class AdminProductUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    slug = serializers.SlugField(
        max_length=220,
        required=False,
        allow_blank=True,
        help_text="Пусто — сгенерировать из названия (только при создании).",
    )
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    price_kopecks = serializers.IntegerField(min_value=1, max_value=MAX_PRICE_KOPECKS)
    compare_at_kopecks = serializers.IntegerField(
        min_value=1, max_value=MAX_PRICE_KOPECKS, allow_null=True, required=False
    )
    is_active = serializers.BooleanField(required=False)


class AdminProductCreateSerializer(AdminProductUpdateSerializer):
    variants = AdminVariantSerializer(
        many=True,
        required=False,
        help_text="Варианты (размеры). Не передано — один вариант «Без размера».",
    )
