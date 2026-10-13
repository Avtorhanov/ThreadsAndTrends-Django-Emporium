"""Резервная Django admin (только суперпользователь). Повседневное управление каталогом —
панель администратора (admin-panel/), она соблюдает правила сервисного слоя."""

from django.contrib import admin
from django.db.models import Sum

from .models import Cart, CartItem, Category, Product, ProductImage, ProductVariant
from .services import cart as cart_service


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "slug", "position", "is_active"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name", "slug"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ["size", "sku", "stock", "position", "deleted_at"]

    def get_queryset(self, request):
        return ProductVariant.all_objects.all()


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ["image", "position"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price_kopecks", "is_active", "deleted_at"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "slug"]
    inlines = [ProductVariantInline, ProductImageInline]

    def get_queryset(self, request):
        # Резервный доступ видит и мягко удалённые товары.
        return Product.all_objects.select_related("category")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ["variant", "quantity", "seen_price_kopecks", "added_at"]
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Только просмотр: корзину меняет покупатель через приложение."""

    list_display = ["owner", "items_quantity"]
    search_fields = ["owner__email"]
    inlines = [CartItemInline]
    fields = ["owner", "total_kopecks"]
    readonly_fields = fields

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("owner")
            .annotate(qty=Sum("items__quantity"))
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Сумма доступных позиций, коп.")
    def total_kopecks(self, obj):
        return cart_service.get_summary(obj.owner).total_kopecks

    @admin.display(description="Единиц товара", ordering="qty")
    def items_quantity(self, obj):
        return obj.qty or 0
