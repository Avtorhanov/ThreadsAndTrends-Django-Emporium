"""Статьи и контакты: публичное чтение (приложение) и раздел «Статьи» панели администратора.
Логика — content.services и content.contacts."""

from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from content import services
from content.contacts import get_contacts
from content.models import Article, ArticleImage
from core.api.mixins import AdminAPIMixin, PublicAPIMixin

from .serializers import (
    AdminArticleDetailSerializer,
    AdminArticleImageReorderSerializer,
    AdminArticleImageSerializer,
    AdminArticleImageUploadSerializer,
    AdminArticleSerializer,
    AdminArticleWriteSerializer,
    ArticleDetailSerializer,
    ArticleSerializer,
    ContactSerializer,
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
