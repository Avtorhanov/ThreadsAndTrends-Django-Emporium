from django.contrib import admin
from carts.models import CartItem, Cart


# Register your models here.
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

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

    total_price.short_description = 'Total Price'
    total_quantity.short_description = 'Total Quantity'

admin.site.register(Cart, CartAdmin)