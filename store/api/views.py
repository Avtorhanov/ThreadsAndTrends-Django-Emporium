"""Публичный каталог для мобильного приложения и веб-витрины: только активные
и неудалённые товары в активных категориях; поиск, фильтры и сортировка."""

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from core.api.mixins import PublicAPIMixin
from store.models import Product, ProductImage, ProductVariant
from store.services import storefront

from .serializers import (
    CatalogCategoryTreeSerializer,
    CatalogProductDetailSerializer,
    CatalogProductSerializer,
    ProductListQuerySerializer,
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
