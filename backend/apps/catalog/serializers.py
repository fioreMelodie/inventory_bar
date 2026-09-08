"""Serializadores del Módulo 4 - Catálogo de Productos."""
from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Producto del catálogo.

    El valor de compra es visible únicamente para el Administrador; para el
    Cajero y el Mesero se retira de la respuesta (criterio de la HU11).
    """

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "product_type",
            "category",
            "purchase_price",
            "sale_price",
            "image",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        extra_kwargs = {
            "name": {
                "error_messages": {
                    "blank": "Product name is required.",
                    "required": "Product name is required.",
                    "unique": "A product with this name already exists.",
                }
            },
            "product_type": {
                "error_messages": {
                    "blank": "Product type is required.",
                    "required": "Product type is required.",
                }
            },
            "category": {
                "error_messages": {
                    "blank": "Category is required.",
                    "required": "Category is required.",
                }
            },
            "purchase_price": {
                "error_messages": {
                    "required": "Purchase price is required.",
                    "invalid": "Purchase price must be a whole number.",
                    "min_value": "Purchase price must be a positive number.",
                }
            },
            "sale_price": {
                "error_messages": {
                    "required": "Sale price is required.",
                    "invalid": "Sale price must be a whole number.",
                    "min_value": "Sale price must be a positive number.",
                }
            },
        }

    def validate_name(self, value):
        """El nombre debe ser único en el catálogo."""
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Product name is required.")

        duplicates = Product.objects.filter(name__iexact=name)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A product with this name already exists.")

        return name

    def validate_purchase_price(self, value):
        """El valor de compra es obligatorio y debe ser positivo."""
        if value <= 0:
            raise serializers.ValidationError("Purchase price must be greater than zero.")
        return value

    def validate_sale_price(self, value):
        """El valor de venta es obligatorio y debe ser positivo."""
        if value <= 0:
            raise serializers.ValidationError("Sale price must be greater than zero.")
        return value

    def to_representation(self, instance):
        """Oculta el valor de compra a los roles que no deben verlo."""
        data = super().to_representation(instance)

        request = self.context.get("request")
        if request is not None and not request.user.is_admin:
            data.pop("purchase_price", None)

        return data
