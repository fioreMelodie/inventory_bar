from django.contrib import admin

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Las facturas son de solo lectura, incluso para el superusuario."""

    list_display = ("number", "created_at", "venue", "total", "payment_method", "cashier")
    list_filter = ("payment_method", "venue", "created_at")
    search_fields = ("number",)
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
