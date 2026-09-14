"""Serializadores del Módulo 5 - Gestión de Proveedores."""
from rest_framework import serializers

from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    """
    Proveedor.

    El nombre es obligatorio y único; teléfono y correo son opcionales pero
    recomendados (criterio de la HU12).
    """

    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "name": {
                "error_messages": {
                    "blank": "Supplier name is required.",
                    "required": "Supplier name is required.",
                    "unique": "A supplier with this name already exists.",
                }
            },
            "email": {"error_messages": {"invalid": "Enter a valid email address."}},
        }

    def validate_name(self, value):
        """El nombre del proveedor no puede estar duplicado."""
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Supplier name is required.")

        duplicates = Supplier.objects.filter(name__iexact=name)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A supplier with this name already exists.")

        return name
