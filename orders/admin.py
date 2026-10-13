"""Резервная Django admin (только суперпользователь): заказы только для просмотра.
Статусы меняются в панели администратора через state machine (orders.services.status)."""

from django.contrib import admin

from orders.models import Order, OrderItem, OrderStatusChange


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class OrderItemInline(ReadOnlyInline):
    model = OrderItem
    fields = ["product_name", "size", "sku", "price_kopecks", "quantity"]
    readonly_fields = fields


class OrderStatusChangeInline(ReadOnlyInline):
    model = OrderStatusChange
    fields = ["from_status", "to_status", "changed_by", "actor", "created_at"]
    readonly_fields = fields


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "number",
        "owner",
        "status",
        "payment_method",
        "delivery_method",
        "total_kopecks",
        "created_at",
    ]
    list_filter = ["status", "payment_method", "delivery_method"]
    search_fields = ["number", "owner__email", "recipient_phone"]
    list_select_related = ["owner"]
    inlines = [OrderItemInline, OrderStatusChangeInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
