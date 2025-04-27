from django.contrib import admin
from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['owner', 'date_ordered', 'total_price', 'is_ordered', 'address', 'phone_number', 'total_quantity', 'status']
    search_fields = ['owner__username']
    inlines = [OrderItemInline]
    fields = ['owner', 'date_ordered', 'total_price', 'is_ordered', 'address', 'phone_number', 'size', 'status']
    readonly_fields = ['date_ordered', 'total_quantity']

    def total_quantity(self, obj):
        return obj.total_quantity()

    total_quantity.short_description = 'Общее количество'

admin.site.register(Order, OrderAdmin)