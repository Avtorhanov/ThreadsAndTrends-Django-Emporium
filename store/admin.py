from django.contrib import admin
from .models import Category, SubCategory, Product, Cart, CartItem

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    search_fields = ['name']
    list_filter = ['category']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price', 'status']
    search_fields = ['name']
    list_filter = ['category', 'subcategory', 'status']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ['product', 'quantity', 'price', 'product_description']  # Добавляем поле 'product_description'
    readonly_fields = ['product_description']  # Устанавливаем его как только для чтения

    def product_description(self, instance):
        return instance.product.description

    product_description.short_description = 'Описание товара'
class CartAdmin(admin.ModelAdmin):
    list_display = ['owner', 'total_price', 'total_quantity']
    search_fields = ['owner__username']
    inlines = [CartItemInline]
    fieldsets = (
        (None, {
            'fields': ('owner', 'session_key', 'total_price'),
        }),
    )
    readonly_fields = ['total_price']

    def total_price(self, obj):
        return obj.calculate_total_price()
    def total_quantity(self, obj):
        return sum(item.quantity for item in obj.cartitem_set.all())

    total_price.short_description = 'Общая стоимость'
    total_quantity.short_description = 'Общее количество'


admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)