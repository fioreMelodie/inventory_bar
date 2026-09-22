from django.contrib import admin

from .models import Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("identifier", "venue", "status", "is_active")
    list_filter = ("venue", "status", "is_active")
    search_fields = ("identifier",)
