"""Резервная Django admin (только суперпользователь): платежи и возвраты только для просмотра.
Статусы меняются только сверкой с провайдером (payments.services)."""

from django.contrib import admin

from payments.models import Payment, Refund


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    can_delete = False
    fields = ["amount_kopecks", "status", "reason", "provider_refund_id", "created_at"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ["order", "amount_kopecks", "status", "provider_payment_id", "created_at"]
    list_filter = ["status"]
    search_fields = ["order__number", "provider_payment_id"]
    list_select_related = ["order"]
    inlines = [RefundInline]


@admin.register(Refund)
class RefundAdmin(ReadOnlyAdmin):
    list_display = ["payment", "amount_kopecks", "status", "reason", "created_at"]
    list_filter = ["status", "reason"]
    search_fields = ["payment__order__number", "provider_refund_id"]
    list_select_related = ["payment__order"]
