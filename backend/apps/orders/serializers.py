"""Serializadores del Módulo 8 - Gestión de Pedidos."""
from rest_framework import serializers

from apps.accounts.models import Role
from apps.tables.models import Table, TableStatus

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    """Pedido con los datos que la interfaz necesita mostrar."""

    table_identifier = serializers.CharField(source="table.identifier", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    waiter_name = serializers.CharField(source="waiter.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "venue",
            "venue_name",
            "table",
            "table_identifier",
            "waiter",
            "waiter_name",
            "status",
            "status_label",
            "total",
            "opened_at",
            "sent_to_cashier_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    """
    Apertura de un pedido sobre una mesa libre (HU19).

    La sede y el mesero no se reciben del cliente: se deducen de la mesa y de
    la sesión, de modo que no puedan falsearse.
    """

    table = serializers.PrimaryKeyRelatedField(
        queryset=Table.objects.filter(is_active=True),
        error_messages={
            "required": "Select a table to open the order.",
            "does_not_exist": "Select a valid table.",
        },
    )

    def validate_table(self, value):
        user = self.context["request"].user

        # El Mesero solo opera las mesas de su sede asignada.
        if user.role != Role.ADMIN and value.venue != user.venue:
            raise serializers.ValidationError(
                "You can only open orders for tables in your own venue."
            )

        if value.status != TableStatus.FREE:
            raise serializers.ValidationError(
                "This table is occupied. Only free tables can take a new order."
            )

        return value
