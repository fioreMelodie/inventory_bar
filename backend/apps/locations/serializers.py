"""Serializadores del Módulo 2 - Administración de Sedes."""
from rest_framework import serializers

from .models import Venue


class VenueSerializer(serializers.ModelSerializer):
    """
    Sede del negocio.

    El nombre es obligatorio y único; la dirección es opcional (HU04).
    """

    class Meta:
        model = Venue
        fields = ("id", "name", "address", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "is_active", "created_at", "updated_at")
        extra_kwargs = {
            "name": {
                "error_messages": {
                    "blank": "Venue name is required.",
                    "required": "Venue name is required.",
                    "unique": "A venue with this name already exists.",
                }
            }
        }

    def validate_name(self, value):
        """Normaliza el nombre y verifica que no exista otra sede igual."""
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Venue name is required.")

        duplicates = Venue.objects.filter(name__iexact=name)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("A venue with this name already exists.")

        return name
