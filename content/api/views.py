"""Статьи и контакты: публичное чтение (приложение) и раздел «Статьи» панели администратора.
Логика — content.services и content.contacts."""

from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from content import home, look, services, shop, site
from content.contacts import get_contacts
from content.models import Article, ArticleImage, Block, BlockArea, HomeBlock
from core.api.mixins import AdminAPIMixin, PublicAPIMixin

from .serializers import (
    AdminArticleDetailSerializer,
    AdminArticleImageReorderSerializer,
    AdminArticleImageSerializer,
    AdminArticleImageUploadSerializer,
    AdminArticleSerializer,
    AdminArticleWriteSerializer,
    AdminBlockAreaSerializer,
    AdminBlockReorderSerializer,
    AdminBlockSerializer,
    AdminBlockUpdateSerializer,
    AdminHomeBlockCreateSerializer,
    AdminHomeBlockSerializer,
    AdminHomeBlockUpdateSerializer,
    AdminHomeImageUploadSerializer,
    AdminHomeReorderSerializer,
    AdminHomeSerializer,
    AdminShopSettingsSerializer,
    AdminShopSettingsWriteSerializer,
    AdminSiteTextSerializer,
    AdminThemeSerializer,
    AdminThemeWriteSerializer,
    ArticleDetailSerializer,
    ArticleSerializer,
    ContactSerializer,
    HomeSerializer,
    ShopThemeSerializer,
)

TAG = "content"
ADMIN_TAG = "admin-content"
PUBLIC_LIMIT = 100


def _with_images(queryset):
    return queryset.prefetch_related(
        Prefetch("images", queryset=ArticleImage.objects.order_by("position", "id"))
    )


@extend_schema(tags=[TAG])
class ArticleListView(PublicAPIMixin, generics.ListAPIView):
    """Опубликованные статьи, новые сверху (до 100, без страниц)."""

    serializer_class = ArticleSerializer
    pagination_class = None

    def get_queryset(self):
        return _with_images(Article.objects.published().order_by("-published_at", "-id"))[
            :PUBLIC_LIMIT
        ]

    @extend_schema(operation_id="content_articles_list")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ArticleDetailView(PublicAPIMixin, generics.RetrieveAPIView):
    """Статья с абзацами и фото. Черновик и удалённая — 404."""

    serializer_class = ArticleDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return _with_images(Article.objects.published())

    @extend_schema(operation_id="content_articles_retrieve")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ContactListView(PublicAPIMixin, generics.ListAPIView):
    """Каналы связи магазина (настройки сервера). Пустые не возвращаются."""

    serializer_class = ContactSerializer
    pagination_class = None

    @extend_schema(operation_id="content_contacts_list")
    def get(self, request, *args, **kwargs):
        return Response(ContactSerializer(get_contacts(), many=True).data)


class ArticleStatus:
    PUBLISHED = "published"
    DRAFT = "draft"
    DELETED = "deleted"
    CHOICES = [PUBLISHED, DRAFT, DELETED]


@extend_schema(tags=[ADMIN_TAG])
class AdminArticleViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Статьи, включая черновики и удалённые (фильтр status)."""

    section = "articles"

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        return AdminArticleSerializer if self.action == "list" else AdminArticleDetailSerializer

    def get_queryset(self):
        queryset = _with_images(
            Article.all_objects.annotate(images_count=Count("images", distinct=True))
        ).order_by("-created_at", "-id")
        if self.action != "list":
            return queryset
        params = self.request.query_params
        article_status = params.get("status")
        if article_status == ArticleStatus.PUBLISHED:
            queryset = queryset.filter(deleted_at__isnull=True, is_published=True)
        elif article_status == ArticleStatus.DRAFT:
            queryset = queryset.filter(deleted_at__isnull=True, is_published=False)
        elif article_status == ArticleStatus.DELETED:
            queryset = queryset.filter(deleted_at__isnull=False)
        else:
            queryset = queryset.filter(deleted_at__isnull=True)
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset

    def _detail(self, article, status_code=status.HTTP_200_OK):
        fresh = self.get_queryset().get(pk=article.pk)
        data = AdminArticleDetailSerializer(fresh, context=self.get_serializer_context()).data
        return Response(data, status=status_code)

    @extend_schema(
        operation_id="admin_content_articles_list",
        parameters=[
            OpenApiParameter("search", str, description="Поиск по заголовку"),
            OpenApiParameter(
                "status",
                str,
                enum=ArticleStatus.CHOICES,
                description="По умолчанию — кроме удалённых",
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(operation_id="admin_content_articles_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        operation_id="admin_content_articles_create",
        request=AdminArticleWriteSerializer,
        responses={201: AdminArticleDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = AdminArticleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = services.create_article(**serializer.validated_data)
        return self._detail(article, status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="admin_content_articles_partial_update",
        request=AdminArticleWriteSerializer,
        responses={200: AdminArticleDetailSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        article = self.get_object()
        serializer = AdminArticleWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_article(article, **serializer.validated_data)
        return self._detail(article)

    @extend_schema(
        operation_id="admin_content_articles_destroy",
        responses={204: None},
        description="Мягкое удаление: статья пропадает с сайта и из приложения.",
    )
    def destroy(self, request, *args, **kwargs):
        services.delete_article(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses={200: AdminArticleDetailSerializer})
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        return self._detail(services.restore_article(self.get_object()))

    @extend_schema(
        request=AdminArticleImageUploadSerializer,
        responses={201: AdminArticleImageSerializer},
        description="Загрузить фото в конец (JPEG/PNG/WebP, до 5 МБ, до 6 фото); первое — обложка.",
    )
    @action(detail=True, methods=["post"], url_path="images", parser_classes=[MultiPartParser])
    def add_image(self, request, pk=None):
        serializer = AdminArticleImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = services.add_article_image(self.get_object(), serializer.validated_data["image"])
        data = AdminArticleImageSerializer(image, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=AdminArticleImageReorderSerializer,
        responses={200: AdminArticleImageSerializer(many=True)},
    )
    @action(detail=True, methods=["post"], url_path="images/reorder", pagination_class=None)
    def reorder_images(self, request, pk=None):
        serializer = AdminArticleImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = services.reorder_article_images(
            self.get_object(), serializer.validated_data["ids"]
        )
        context = self.get_serializer_context()
        return Response(AdminArticleImageSerializer(images, many=True, context=context).data)


@extend_schema(tags=[ADMIN_TAG])
class AdminArticleImageViewSet(AdminAPIMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    section = "articles"

    serializer_class = AdminArticleImageSerializer
    queryset = ArticleImage.objects.all()
    http_method_names = ["delete", "options"]

    @extend_schema(
        operation_id="admin_content_article_images_destroy",
        responses={204: OpenApiResponse(description="Фото и файл удалены")},
    )
    def destroy(self, request, *args, **kwargs):
        services.delete_article_image(get_object_or_404(ArticleImage, pk=kwargs["pk"]))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Тексты и блоки витрины: правка администратором прямо на сайте ---


@extend_schema(tags=[ADMIN_TAG])
class AdminSiteTextView(AdminAPIMixin, generics.GenericAPIView):
    """Текст витрины по ключу: PUT — сохранить (пусто — скрыть), DELETE — вернуть исходный."""

    section = "storefront"

    serializer_class = AdminSiteTextSerializer

    @extend_schema(operation_id="admin_content_texts_update")
    def put(self, request, key: str):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = site.set_text(key, serializer.validated_data["value"])
        return Response({"key": text.key, "value": text.value})

    @extend_schema(operation_id="admin_content_texts_reset", responses={204: None})
    def delete(self, request, key: str):
        site.reset_text(key)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[ADMIN_TAG])
class AdminBlockViewSet(
    AdminAPIMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """Блоки разделов «Контакты», «Помощь» и подвала. Первое изменение раздела переносит его
    значения по умолчанию в БД (customize) — дальше блоки меняются по id."""

    section = "storefront"

    serializer_class = AdminBlockSerializer
    pagination_class = None
    queryset = Block.objects.order_by("area", "position", "id")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    @extend_schema(
        operation_id="admin_content_blocks_list",
        parameters=[OpenApiParameter("area", str, enum=BlockArea.values, required=True)],
    )
    def list(self, request, *args, **kwargs):
        area = AdminBlockAreaSerializer(data=request.query_params)
        area.is_valid(raise_exception=True)
        blocks = site.blocks(area.validated_data["area"])
        return Response(AdminBlockSerializer(blocks, many=True).data)

    @extend_schema(operation_id="admin_content_blocks_create", request=AdminBlockSerializer)
    def create(self, request):
        serializer = AdminBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = site.add_block(**serializer.validated_data)
        return Response(AdminBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="admin_content_blocks_partial_update",
        request=AdminBlockUpdateSerializer,
        responses=AdminBlockSerializer,
    )
    def partial_update(self, request, pk=None):
        serializer = AdminBlockUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = site.update_block(self.get_object(), **serializer.validated_data)
        return Response(AdminBlockSerializer(block).data)

    def perform_destroy(self, instance):
        site.delete_block(instance)

    @extend_schema(
        operation_id="admin_content_blocks_customize",
        request=AdminBlockAreaSerializer,
        responses=AdminBlockSerializer(many=True),
    )
    @action(detail=False, methods=["post"])
    def customize(self, request):
        """Перенести раздел в БД (идемпотентно) — ответ: блоки с id в порядке показа."""
        serializer = AdminBlockAreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blocks = site.customize(serializer.validated_data["area"])
        return Response(AdminBlockSerializer(blocks, many=True).data)

    @extend_schema(
        operation_id="admin_content_blocks_reorder",
        request=AdminBlockReorderSerializer,
        responses=AdminBlockSerializer(many=True),
    )
    @action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = AdminBlockReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blocks = site.reorder_blocks(**serializer.validated_data)
        return Response(AdminBlockSerializer(blocks, many=True).data)


# --- Настройки магазина ---


@extend_schema(tags=[ADMIN_TAG])
class AdminShopSettingsView(AdminAPIMixin, generics.GenericAPIView):
    """Доставка, оплата и реквизиты продавца. Пустое поле — значение из .env (`defaults`)."""

    section = "settings"

    serializer_class = AdminShopSettingsSerializer

    @extend_schema(operation_id="admin_content_settings_retrieve")
    def get(self, request):
        return Response(AdminShopSettingsSerializer(shop.get_row()).data)

    @extend_schema(
        operation_id="admin_content_settings_update",
        request=AdminShopSettingsWriteSerializer,
        responses=AdminShopSettingsSerializer,
    )
    def put(self, request):
        serializer = AdminShopSettingsWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = shop.update(**serializer.validated_data)
        return Response(AdminShopSettingsSerializer(row).data)


# --- Главная из блоков ---


@extend_schema(tags=[TAG])
class HomeView(PublicAPIMixin, generics.GenericAPIView):
    """Опубликованная главная: блоки по порядку с товарами и категориями."""

    serializer_class = HomeSerializer

    @extend_schema(operation_id="content_home_retrieve")
    def get(self, request):
        blocks = home.published_blocks()
        return Response(HomeSerializer({"blocks": blocks}, context={"request": request}).data)


def _admin_home(request) -> Response:
    page = home.get_page()
    data = {
        "blocks": home.draft_blocks(),
        "has_changes": home.has_changes(page),
        "published_at": page.published_at,
    }
    return Response(AdminHomeSerializer(data, context={"request": request}).data)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomeView(AdminAPIMixin, generics.GenericAPIView):
    """Черновик главной: все блоки (и скрытые), есть ли неопубликованные правки."""

    section = "storefront"

    serializer_class = AdminHomeSerializer

    @extend_schema(operation_id="admin_content_home_retrieve")
    def get(self, request):
        return _admin_home(request)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomePublishView(AdminAPIMixin, generics.GenericAPIView):
    section = "storefront"

    serializer_class = AdminHomeSerializer

    @extend_schema(
        operation_id="admin_content_home_publish",
        request=None,
        description="Опубликовать черновик: покупатели увидят видимые блоки в этом порядке.",
    )
    def post(self, request):
        home.publish()
        return _admin_home(request)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomeReorderView(AdminAPIMixin, generics.GenericAPIView):
    """Новый порядок блоков главной (все id, каждый один раз)."""

    section = "storefront"

    serializer_class = AdminHomeReorderSerializer

    @extend_schema(operation_id="admin_content_home_reorder", responses=AdminHomeSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        home.reorder_blocks(serializer.validated_data["ids"])
        return _admin_home(request)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomeBlockCreateView(AdminAPIMixin, generics.GenericAPIView):
    section = "storefront"

    serializer_class = AdminHomeBlockCreateSerializer

    @extend_schema(
        operation_id="admin_content_home_blocks_create",
        responses={201: AdminHomeBlockSerializer},
        description="Новый блок в конец страницы с текстом по умолчанию.",
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = home.add_block(serializer.validated_data["kind"])
        data = AdminHomeBlockSerializer(block, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomeBlockView(AdminAPIMixin, generics.GenericAPIView):
    """Блок главной: правка в черновик или удаление."""

    section = "storefront"

    serializer_class = AdminHomeBlockUpdateSerializer
    queryset = HomeBlock.objects.all()

    @extend_schema(
        operation_id="admin_content_home_blocks_partial_update",
        responses=AdminHomeBlockSerializer,
    )
    def patch(self, request, pk: int):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = home.update_block(self.get_object(), **serializer.validated_data)
        return Response(AdminHomeBlockSerializer(block, context={"request": request}).data)

    @extend_schema(operation_id="admin_content_home_blocks_destroy", responses={204: None})
    def delete(self, request, pk: int):
        home.delete_block(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[ADMIN_TAG])
class AdminHomeBlockImageView(AdminAPIMixin, generics.GenericAPIView):
    """Картинка баннера: загрузить (заменяет прежнюю) или убрать."""

    section = "storefront"

    serializer_class = AdminHomeImageUploadSerializer
    queryset = HomeBlock.objects.all()
    parser_classes = [MultiPartParser]

    @extend_schema(
        operation_id="admin_content_home_blocks_image_create",
        responses=AdminHomeBlockSerializer,
        description="Картинка баннера (JPEG/PNG/WebP, до 5 МБ); заменяет прежнюю.",
    )
    def post(self, request, pk: int):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = home.set_banner_image(self.get_object(), serializer.validated_data["image"])
        return Response(AdminHomeBlockSerializer(block, context={"request": request}).data)

    @extend_schema(
        operation_id="admin_content_home_blocks_image_destroy",
        request=None,
        responses={200: AdminHomeBlockSerializer},
    )
    def delete(self, request, pk: int):
        block = home.remove_banner_image(self.get_object())
        return Response(AdminHomeBlockSerializer(block, context={"request": request}).data)


# --- Тема для покупателей ---


def _theme_data(*, all_palettes: bool = False) -> dict:
    theme = look.shop_theme()
    keys = list(look.PALETTES) if all_palettes else list(theme.palettes)
    return {
        "palettes": [look.PALETTES[key] for key in keys],
        "accents": list(look.ACCENTS.values()),
        "default_palette": theme.default_palette,
        "default_mode": theme.default_mode,
        "default_radius": theme.default_radius,
        "nav_style": theme.nav_style,
        "enabled": list(theme.palettes),
    }


@extend_schema(tags=[TAG])
class ShopThemeView(PublicAPIMixin, generics.GenericAPIView):
    """Палитры, доступные покупателю, и оформление для нового посетителя (приложение)."""

    serializer_class = ShopThemeSerializer

    @extend_schema(operation_id="content_theme_retrieve")
    def get(self, request):
        return Response(ShopThemeSerializer(_theme_data()).data)


@extend_schema(tags=[ADMIN_TAG])
class AdminThemeView(AdminAPIMixin, generics.GenericAPIView):
    """Панель → «Тема»: все палитры, какие доступны покупателям, оформление по умолчанию."""

    section = "storefront"

    serializer_class = AdminThemeSerializer

    @extend_schema(operation_id="admin_content_theme_retrieve")
    def get(self, request):
        return Response(AdminThemeSerializer(_theme_data(all_palettes=True)).data)

    @extend_schema(
        operation_id="admin_content_theme_update",
        request=AdminThemeWriteSerializer,
        responses=AdminThemeSerializer,
    )
    def put(self, request):
        serializer = AdminThemeWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        look.update(**serializer.validated_data)
        return Response(AdminThemeSerializer(_theme_data(all_palettes=True)).data)
