"""Резервная Django admin (только суперпользователь). Повседневное управление каталогом —
панель администратора (admin-panel/), она соблюдает правила сервисного слоя."""

from django.contrib import admin

from .models import Cart, CartItem, Category, Product, ProductImage, ProductVariant


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
    fields = ["product", "quantity", "price_kopecks"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["owner", "total_kopecks", "total_quantity"]
    search_fields = ["owner__email"]
    inlines = [CartItemInline]
    fields = ["owner", "session_key", "total_kopecks"]
    readonly_fields = ["total_kopecks"]

    @admin.display(description="Общая стоимость, коп.")
    def total_kopecks(self, obj):
        return obj.calculate_total_kopecks()

    @admin.display(description="Общее количество")
    def total_quantity(self, obj):
        return sum(item.quantity for item in obj.cartitem_set.all())
