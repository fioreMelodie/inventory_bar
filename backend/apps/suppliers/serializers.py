"""Serializadores del Módulo 5 - Gestión de Proveedores."""
from rest_framework import serializers

from apps.catalog.models import Product

from .models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    """
    Proveedor.

    El nombre es obligatorio y único; teléfono y correo son opcionales pero
    recomendados (criterio de la HU12).
    """

    # Ahora que existe la relación proveedor-producto (HU13), se informa
    # cuántos productos suministra cada proveedor.
    product_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Supplier
        fields = (
            "id",
            "name",
            "phone",
            "email",
            "product_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "product_count", "created_at", "updated_at")
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


class SupplierProductsSerializer(serializers.Serializer):
    """
    Asociación de productos del catálogo a un proveedor (HU13).

    Se envía la lista completa de productos que suministra el proveedor: los
    que se omiten quedan desvinculados, lo que permite modificar o eliminar la
    asociación con una sola operación.
    """

    products = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        many=True,
        allow_empty=True,
    )
