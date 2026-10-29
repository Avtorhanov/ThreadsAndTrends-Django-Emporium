"""Публичный каталог для мобильного приложения и веб-витрины: только активные
и неудалённые товары в активных категориях; поиск, фильтры и сортировка."""

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.mixins import PublicAPIMixin
from store.models import Product, ProductImage, ProductVariant
from store.services import history, storefront

from .serializers import (
    CatalogCategoryTreeSerializer,
    CatalogProductDetailSerializer,
    CatalogProductSerializer,
    ProductListQuerySerializer,
    ViewedRecordSerializer,
)

TAG = "catalog"


@extend_schema(tags=[TAG])
class CategoryTreeView(PublicAPIMixin, generics.ListAPIView):
    """Дерево активных категорий: корни с подкатегориями (из кэша)."""

    serializer_class = CatalogCategoryTreeSerializer
    pagination_class = None

    @extend_schema(operation_id="catalog_categories_list")
    def get(self, request, *args, **kwargs):
        return Response(storefront.category_tree())


@extend_schema(tags=[TAG])
class ProductListView(PublicAPIMixin, generics.ListAPIView):
    """Лента товаров: поиск (`q`, только товары в наличии), категория с подкатегориями,
    цена в копейках, наличие, сортировка. Постранично."""

    serializer_class = CatalogProductSerializer

    def get_queryset(self):
        params = ProductListQuerySerializer(data=self.request.query_params)
        params.is_valid(raise_exception=True)
        data = params.validated_data
        category = None
        if data.get("category"):
            category = get_object_or_404(storefront.active_categories(), slug=data["category"])
        return storefront.filter_products(
            storefront.ProductFilters(
                q=data.get("q", ""),
                category=category,
                price_min=data.get("price_min"),
                price_max=data.get("price_max"),
                in_stock=data.get("in_stock", False),
                sort=data.get("sort", ""),
            )
        )

    @extend_schema(operation_id="catalog_products_list", parameters=[ProductListQuerySerializer])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ProductDetailView(PublicAPIMixin, generics.RetrieveAPIView):
    serializer_class = CatalogProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.live()
            .select_related("category", "status")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.order_by("position", "id")),
                Prefetch("variants", queryset=ProductVariant.objects.order_by("position", "id")),
            )
        )

    @extend_schema(operation_id="catalog_products_retrieve")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class SimilarProductsView(PublicAPIMixin, generics.ListAPIView):
    """«Похожие» для карточки товара: та же категория, затем соседние; до 12, без страниц."""

    serializer_class = CatalogProductSerializer
    pagination_class = None

    def get_queryset(self):
        product = get_object_or_404(
            Product.objects.live().select_related("category"), slug=self.kwargs["slug"]
        )
        return storefront.similar_products(product)

    @extend_schema(operation_id="catalog_products_similar")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ViewedProductsView(APIView):
    """Журнал просмотров покупателя: последние товары (без страниц), запись и очистка."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CatalogProductSerializer(many=True)}, operation_id="viewed_list")
    def get(self, request):
        products = history.recent_products(request.user, limit=history.HISTORY_LIMIT)
        return Response(
            CatalogProductSerializer(products, many=True, context={"request": request}).data
        )

    @extend_schema(
        request=ViewedRecordSerializer, responses={204: None}, operation_id="viewed_record"
    )
    def post(self, request):
        serializer = ViewedRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = get_object_or_404(Product.objects.live(), slug=serializer.validated_data["slug"])
        history.record_view(request.user, product)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None}, operation_id="viewed_clear")
    def delete(self, request):
        history.clear(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
