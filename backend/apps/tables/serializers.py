"""Serializadores del Módulo 7 - Gestión de Mesas."""
from django.utils import timezone
from rest_framework import serializers

from apps.locations.models import Venue

from .models import Table, TableStatus


class TableSerializer(serializers.ModelSerializer):
    """
    Mesa de una sede.

    El identificador debe ser único dentro de la sede, no en todo el sistema.
    """

    venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.filter(is_active=True))
    venue_name = serializers.CharField(source="venue.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Table
        fields = (
            "id",
            "venue",
            "venue_name",
            "identifier",
            "status",
            "status_label",
            "is_active",
            "created_at",
        )
        # El estado no se asigna a mano: lo determinan los pedidos.
        read_only_fields = ("id", "venue_name", "status", "status_label", "created_at")
        extra_kwargs = {
            "identifier": {
                "error_messages": {
                    "blank": "Table identifier is required.",
                    "required": "Table identifier is required.",
                }
            },
            "venue": {
                "error_messages": {
                    "required": "Select the venue this table belongs to.",
                    "does_not_exist": "Select a valid venue.",
                }
            },
        }

    def validate_identifier(self, value):
        identifier = value.strip()
        if not identifier:
            raise serializers.ValidationError("Table identifier is required.")
        return identifier

    def validate(self, attrs):
        """
        Verifica la unicidad del identificador dentro de la sede y que la mesa
        no tenga un pedido activo cuando se la quiere renombrar.
        """
        venue = attrs.get("venue", getattr(self.instance, "venue", None))
        identifier = attrs.get("identifier", getattr(self.instance, "identifier", None))

        duplicates = Table.objects.filter(venue=venue, identifier__iexact=identifier)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"identifier": "This venue already has a table with that identifier."}
            )

        # El Administrador puede editar el identificador solo si la mesa no
        # tiene pedidos activos (criterio de la HU17).
        if (
            self.instance is not None
            and identifier != self.instance.identifier
            and self.instance.status == TableStatus.OCCUPIED
        ):
            raise serializers.ValidationError(
                {"identifier": "This table has an active order and cannot be renamed."}
            )

        return attrs


class RoomTableSerializer(serializers.ModelSerializer):
    """
    Mesa tal como se presenta en la vista de sala (HU18).

    Añade el pedido activo y el tiempo transcurrido desde su apertura, para
    que el personal identifique de un vistazo qué mesas llevan más tiempo
    ocupadas.
    """

    active_order = serializers.SerializerMethodField()
    occupied_since = serializers.SerializerMethodField()
    occupied_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = (
            "id",
            "identifier",
            "status",
            "venue",
            "active_order",
            "occupied_since",
            "occupied_minutes",
        )
        read_only_fields = fields

    def get_active_order(self, table):
        order = self._active_order(table)
        return order.id if order else None

    def get_occupied_since(self, table):
        order = self._active_order(table)
        return order.opened_at if order else None

    def get_occupied_minutes(self, table):
        """Minutos completos transcurridos desde la apertura del pedido."""
        order = self._active_order(table)
        if order is None:
            return None

        elapsed = timezone.now() - order.opened_at
        return int(elapsed.total_seconds() // 60)

    def _active_order(self, table):
        # El queryset de la vista precarga los pedidos abiertos, de modo que
        # no se consulta la base de datos una vez por mesa.
        orders = getattr(table, "open_orders", None)
        if orders is None:
            return None
        return orders[0] if orders else None
