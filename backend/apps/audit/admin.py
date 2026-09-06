from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Los eventos de auditoría son de solo lectura, incluso para el superusuario."""

    list_display = ("created_at", "username", "event_type", "entity", "ip_address")
    list_filter = ("event_type", "created_at")
    search_fields = ("username", "entity", "description")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
