"""Admin API каталога для панели администратора (сессия Django + CSRF, роль IsAdmin).
Вся бизнес-логика — в store.services.catalog."""

from django.db.models import Count, Prefetch, Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from core.api.mixins import AdminAPIMixin
from store.models import Category, Product, ProductImage, ProductVariant
from store.services import catalog

from .serializers import (
    AdminCategorySerializer,
    AdminImageReorderSerializer,
    AdminImageSerializer,
    AdminImageUploadSerializer,
    AdminProductCreateSerializer,
    AdminProductDetailSerializer,
    AdminProductSerializer,
    AdminProductUpdateSerializer,
    AdminVariantSerializer,
)

TAG = "admin-catalog"


class ProductStatus:
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    CHOICES = [ACTIVE, INACTIVE, DELETED]


class StockFilter:
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    CHOICES = [IN_STOCK, OUT_OF_STOCK]


@extend_schema(tags=[TAG])
class AdminCategoryViewSet(
    AdminAPIMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Все категории плоским списком (включая скрытые); дерево строит панель по parent."""

    serializer_class = AdminCategorySerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Category.objects.select_related("parent").annotate(
            products_count=Count(
                "products", filter=Q(products__deleted_at__isnull=True), distinct=True
            ),
            children_count=Count("children", distinct=True),
        )

    def _respond(self, category, status_code=status.HTTP_200_OK):
        fresh = self.get_queryset().get(pk=category.pk)
        return Response(self.get_serializer(fresh).data, status=status_code)

    @extend_schema(operation_id="admin_catalog_categories_list")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(operation_id="admin_catalog_categories_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(operation_id="admin_catalog_categories_create")
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = catalog.create_category(**serializer.validated_data)
        return self._respond(category, status.HTTP_201_CREATED)

    @extend_schema(operation_id="admin_catalog_categories_partial_update")
    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = self.get_serializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        catalog.update_category(category, **serializer.validated_data)
        return self._respond(category)

    @extend_schema(
        operation_id="admin_catalog_categories_destroy",
        description="Физическое удаление пустой категории. С товарами (в т.ч. удалёнными) "
        "или подкатегориями — 400: такую категорию можно только скрыть.",
    )
    def destroy(self, request, *args, **kwargs):
        catalog.delete_category(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
class AdminProductViewSet(
    AdminAPIMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Товары, включая скрытые и удалённые (фильтр status)."""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        return AdminProductSerializer if self.action == "list" else AdminProductDetailSerializer

    def get_queryset(self):
        queryset = (
            Product.all_objects.select_related("category__parent")
            .with_stock()
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.order_by("position", "id"))
            )
            .order_by("-created_at", "-id")
        )
        if self.action != "list":
            return queryset.prefetch_related(
                Prefetch("variants", queryset=ProductVariant.objects.order_by("position", "id"))
            )

        params = self.request.query_params
        product_status = params.get("status")
        if product_status == ProductStatus.ACTIVE:
            queryset = queryset.filter(deleted_at__isnull=True, is_active=True)
        elif product_status == ProductStatus.INACTIVE:
            queryset = queryset.filter(deleted_at__isnull=True, is_active=False)
        elif product_status == ProductStatus.DELETED:
            queryset = queryset.filter(deleted_at__isnull=False)
        else:
            queryset = queryset.filter(deleted_at__isnull=True)

        category_id = params.get("category")
        if category_id and category_id.isdigit():
            queryset = queryset.filter(
                Q(category_id=category_id) | Q(category__parent_id=category_id)
            )

        stock = params.get("stock")
        if stock == StockFilter.IN_STOCK:
            queryset = queryset.filter(total_stock__gt=0)
        elif stock == StockFilter.OUT_OF_STOCK:
            queryset = queryset.filter(Q(total_stock__isnull=True) | Q(total_stock=0))

        search = params.get("search", "").strip()
        if search:
            # Подзапрос, а не join по вариантам: join исказил бы сумму остатков.
            by_sku = ProductVariant.objects.filter(sku__icontains=search).values("product_id")
            queryset = queryset.filter(Q(name__icontains=search) | Q(pk__in=by_sku))
        return queryset

    def _detail(self, product, status_code=status.HTTP_200_OK):
        fresh = self.get_queryset().get(pk=product.pk)
        serializer = AdminProductDetailSerializer(fresh, context=self.get_serializer_context())
        return Response(serializer.data, status=status_code)

    @extend_schema(
        operation_id="admin_catalog_products_list",
        parameters=[
            OpenApiParameter("search", str, description="Поиск по названию и артикулу"),
            OpenApiParameter(
                "status",
                str,
                enum=ProductStatus.CHOICES,
                description="По умолчанию — кроме удалённых",
            ),
            OpenApiParameter("category", int, description="id категории (с подкатегориями)"),
            OpenApiParameter("stock", str, enum=StockFilter.CHOICES),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(operation_id="admin_catalog_products_retrieve")
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        operation_id="admin_catalog_products_create",
        request=AdminProductCreateSerializer,
        responses={201: AdminProductDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = AdminProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = catalog.create_product(**serializer.validated_data)
        return self._detail(product, status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="admin_catalog_products_partial_update",
        request=AdminProductUpdateSerializer,
        responses={200: AdminProductDetailSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = AdminProductUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        catalog.update_product(product, **serializer.validated_data)
        return self._detail(product)

    @extend_schema(
        operation_id="admin_catalog_products_destroy",
        responses={204: None},
        description="Мягкое удаление: товар пропадает с витрины, история заказов сохраняется.",
    )
    def destroy(self, request, *args, **kwargs):
        catalog.soft_delete_product(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=None,
        responses={200: AdminProductDetailSerializer},
        description="Восстановить мягко удалённый товар.",
    )
    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        return self._detail(catalog.restore_product(self.get_object()))

    @extend_schema(
        request=AdminVariantSerializer,
        responses={201: AdminVariantSerializer},
        description="Добавить вариант (размер). «Без размера» нельзя сочетать с размерами.",
    )
    @action(detail=True, methods=["post"], url_path="variants")
    def add_variant(self, request, pk=None):
        serializer = AdminVariantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = catalog.create_variant(self.get_object(), **serializer.validated_data)
        return Response(AdminVariantSerializer(variant).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=AdminImageUploadSerializer,
        responses={201: AdminImageSerializer},
        description="Загрузить фото в конец галереи (JPEG/PNG/WebP, до 5 МБ, до 10 фото).",
    )
    @action(detail=True, methods=["post"], url_path="images", parser_classes=[MultiPartParser])
    def add_image(self, request, pk=None):
        serializer = AdminImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = catalog.add_product_image(self.get_object(), serializer.validated_data["image"])
        data = AdminImageSerializer(image, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=AdminImageReorderSerializer,
        responses={200: AdminImageSerializer(many=True)},
        description="Новый порядок галереи; первое фото — обложка.",
    )
    @action(detail=True, methods=["post"], url_path="images/reorder", pagination_class=None)
    def reorder_images(self, request, pk=None):
        serializer = AdminImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = catalog.reorder_product_images(self.get_object(), serializer.validated_data["ids"])
        context = self.get_serializer_context()
        return Response(AdminImageSerializer(images, many=True, context=context).data)


@extend_schema(tags=[TAG])
class AdminVariantViewSet(
    AdminAPIMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = AdminVariantSerializer
    http_method_names = ["patch", "delete", "options"]

    def get_queryset(self):
        return ProductVariant.objects.select_related("product")

    @extend_schema(operation_id="admin_catalog_variants_partial_update")
    def partial_update(self, request, *args, **kwargs):
        variant = self.get_object()
        serializer = self.get_serializer(variant, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        variant = catalog.update_variant(variant, **serializer.validated_data)
        return Response(self.get_serializer(variant).data)

    @extend_schema(
        operation_id="admin_catalog_variants_destroy",
        description="Мягкое удаление. Последний вариант товара удалить нельзя (400).",
    )
    def destroy(self, request, *args, **kwargs):
        catalog.delete_variant(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=[TAG])
class AdminImageViewSet(AdminAPIMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = AdminImageSerializer
    queryset = ProductImage.objects.all()
    http_method_names = ["delete", "options"]

    @extend_schema(
        operation_id="admin_catalog_images_destroy",
        responses={204: OpenApiResponse(description="Изображение и файл удалены")},
    )
    def destroy(self, request, *args, **kwargs):
        catalog.delete_product_image(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)
