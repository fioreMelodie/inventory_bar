"""Serializadores del Módulo 6 - Gestión de Inventario."""
from rest_framework import serializers

from apps.accounts.models import Role
from apps.catalog.models import Product
from apps.locations.models import Venue

from .models import Stock


class StockEntrySerializer(serializers.Serializer):
    """
    Entrada de mercancía al inventario de una sede (HU14).

    El Cajero solo puede registrar entradas en su sede asignada; el
    Administrador, en cualquiera.
    """

    venue = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    # Solo se pueden registrar productos activos del catálogo.
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True)
    )
    quantity = serializers.IntegerField(
        min_value=1,
        error_messages={
            "invalid": "Quantity must be a whole number of units.",
            "min_value": "Quantity must be greater than zero.",
            "required": "Quantity is required.",
        },
    )

    def validate_venue(self, value):
        """
        Determina y autoriza la sede de la entrada.

        El Cajero no puede registrar entradas en una sede distinta a la suya.
        """
        user = self.context["request"].user

        if user.role == Role.ADMIN:
            if value is None:
                raise serializers.ValidationError(
                    "Select the venue where the goods were received."
                )
            return value

        if value is not None and value != user.venue:
            raise serializers.ValidationError(
                "You can only register stock entries for your own venue."
            )

        if user.venue is None:
            raise serializers.ValidationError(
                "Your account has no venue assigned. Contact an administrator."
            )

        return user.venue

    def validate(self, attrs):
        """Garantiza que la sede quede resuelta incluso si no se envió."""
        user = self.context["request"].user

        if attrs.get("venue") is None:
            if user.role == Role.ADMIN:
                raise serializers.ValidationError(
                    {"venue": "Select the venue where the goods were received."}
                )
            if user.venue is None:
                raise serializers.ValidationError(
                    {"venue": "Your account has no venue assigned."}
                )
            attrs["venue"] = user.venue

        return attrs


class StockSerializer(serializers.ModelSerializer):
    """Existencias de un producto en una sede."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_type = serializers.CharField(source="product.product_type", read_only=True)
    category = serializers.CharField(source="product.category", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True)

    class Meta:
        model = Stock
        fields = (
            "id",
            "venue",
            "venue_name",
            "product",
            "product_name",
            "product_type",
            "category",
            "quantity",
            "updated_at",
        )
        read_only_fields = fields


class VenueStockSerializer(serializers.Serializer):
    """
    Stock de un producto en la sede consultada (HU15).

    Se construye a partir del catálogo activo, de modo que los productos que
    nunca han tenido entrada aparecen con stock cero en lugar de desaparecer
    del listado.
    """

    product = serializers.IntegerField(source="id", read_only=True)
    product_name = serializers.CharField(source="name", read_only=True)
    product_type = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    is_out_of_stock = serializers.SerializerMethodField()

    def get_is_out_of_stock(self, obj):
        """Permite resaltar en la interfaz los productos agotados."""
        return obj.quantity == 0
