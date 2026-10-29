from django.contrib import admin

from .models import Invoice, Payment


class ImmutableAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ImmutableAdmin):
    list_display = ("id", "order", "venue", "cashier", "amount", "paid_at")
    list_filter = ("venue", "method")


@admin.register(Invoice)
class InvoiceAdmin(ImmutableAdmin):
    list_display = ("number", "venue", "issued_at")
    search_fields = ("number",)
