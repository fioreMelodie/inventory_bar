"""Serializadores del Módulo 11 - Auditoría y Trazabilidad."""
from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    """
    Evento del log del sistema.

    Todos los campos son de solo lectura: el log es inmutable y la API no
    expone ninguna forma de alterarlo.
    """

    event_type_label = serializers.CharField(
        source="get_event_type_display", read_only=True
    )
    venue_name = serializers.CharField(source="venue.name", default=None, read_only=True)
    user_full_name = serializers.CharField(
        source="user.full_name", default=None, read_only=True
    )

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "created_at",
            "username",
            "user",
            "user_full_name",
            "event_type",
            "event_type_label",
            "entity",
            "entity_id",
            "venue",
            "venue_name",
            "description",
            "ip_address",
        )
        read_only_fields = fields
