from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "full_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("username", "full_name")
    ordering = ("full_name",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("full_name",)}),
        ("Rol y estado", {"fields": ("role", "is_active")}),
        ("Permisos", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "full_name", "role", "password1", "password2"),
        }),
    )
