from rest_framework import serializers

from content.contacts import ContactKind
from content.models import Article, ArticleImage
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
