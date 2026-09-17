from django.contrib import admin

from .models import Stock, StockMovement


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "venue", "quantity", "updated_at")
    list_filter = ("venue",)
    search_fields = ("product__name",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "venue", "product", "movement_type", "quantity",
                    "performed_by")
    list_filter = ("movement_type", "venue")
    date_hierarchy = "created_at"

    def has_change_permission(self, request, obj=None):
        return False
