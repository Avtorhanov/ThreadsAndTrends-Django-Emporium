"""Публичный каталог для мобильного приложения: только активные и неудалённые товары
в активных категориях. Поиск и фильтры витрины — сессия 7."""

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from core.api.mixins import PublicAPIMixin
from store.models import Category, Product, ProductImage, ProductVariant

from .serializers import (
    CatalogCategoryTreeSerializer,
    CatalogProductDetailSerializer,
    CatalogProductSerializer,
)

TAG = "catalog"


def active_categories():
    return Category.objects.filter(is_active=True).filter(
        Q(parent__isnull=True) | Q(parent__is_active=True)
    )


@extend_schema(tags=[TAG])
class CategoryTreeView(PublicAPIMixin, generics.ListAPIView):
    """Дерево активных категорий: корни с подкатегориями."""

    serializer_class = CatalogCategoryTreeSerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
            Prefetch("children", queryset=Category.objects.filter(is_active=True))
        )

    @extend_schema(operation_id="catalog_categories_list")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ProductListView(PublicAPIMixin, generics.ListAPIView):
    serializer_class = CatalogProductSerializer

    def get_queryset(self):
        queryset = (
            Product.objects.live()
            .with_stock()
            .select_related("category")
            .prefetch_related("images")
        )
        slug = self.request.query_params.get("category")
        if slug:
            category = get_object_or_404(active_categories(), slug=slug)
            # Корневая категория показывает товары всех своих подкатегорий.
            queryset = queryset.filter(Q(category=category) | Q(category__parent=category))
        return queryset

    @extend_schema(
        operation_id="catalog_products_list",
        parameters=[
            OpenApiParameter("category", str, description="Slug категории (с подкатегориями)")
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


@extend_schema(tags=[TAG])
class ProductDetailView(PublicAPIMixin, generics.RetrieveAPIView):
    serializer_class = CatalogProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.live()
            .select_related("category")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.order_by("position", "id")),
                Prefetch("variants", queryset=ProductVariant.objects.order_by("position", "id")),
            )
        )

    @extend_schema(operation_id="catalog_products_retrieve")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
