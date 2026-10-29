from django.contrib import admin

from .models import AuditEvent
from apps.accounts.models import Role


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Los eventos de auditoría son de solo lectura, incluso para el superusuario."""

    list_display = ("created_at", "username", "event_type", "entity", "ip_address")
    list_filter = ("event_type", "created_at")
    search_fields = ("username", "entity", "description")
    date_hierarchy = "created_at"

    def has_view_permission(self, request, obj=None):
        return getattr(request.user, "role", None) == Role.ADMIN and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
