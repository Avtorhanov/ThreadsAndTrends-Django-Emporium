from django.contrib import admin
from .models import Category, SubCategory, Product, Cart, Order, OrderItem, CartItem


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    search_fields = ['name']
    list_filter = ['category']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price']
    search_fields = ['name']
    list_filter = ['category', 'subcategory']

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

class CartAdmin(admin.ModelAdmin):
    list_display = ['owner']
    search_fields = ['owner__username']
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['owner', 'total_price', 'is_ordered', 'address', 'phone_number', 'full_name']
    search_fields = ['owner__username']
    inlines = [OrderItemInline]
    fields = ['owner', 'total_price', 'is_ordered', 'address', 'phone_number', 'full_name']



admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
