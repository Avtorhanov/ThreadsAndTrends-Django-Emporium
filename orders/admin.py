from django.contrib import admin
from orders.models import Order, OrderItem


# Register your models here.
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['owner', 'total_price', 'is_ordered', 'address', 'phone_number', 'total_quantity', 'status']
    search_fields = ['owner__username']
    inlines = [OrderItemInline]
    fields = ['owner', 'total_price', 'is_ordered', 'address', 'phone_number', 'full_name', 'status']
    list_filter = ['status']

admin.site.register(Order, OrderAdmin)