from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "venue", "table", "waiter", "status", "total", "opened_at")
    list_filter = ("status", "venue")
    date_hierarchy = "opened_at"

    def has_delete_permission(self, request, obj=None):
        # Los pedidos no se eliminan: quedan registrados de forma permanente.
        return False
