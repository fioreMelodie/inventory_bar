"""
Vistas del Módulo 2 - Administración de Sedes.

HU04: Crear sede.
"""
from rest_framework import mixins, viewsets

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import Venue
from .serializers import VenueSerializer


class VenueViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Sedes del negocio.

    - POST /api/venues/  crea una sede (solo Administrador).
    - GET  /api/venues/  lista las sedes disponibles.

    Las sedes creadas quedan inmediatamente disponibles para la asignación de
    usuarios y mesas y para los filtros de reportes.
    """

    queryset = Venue.objects.all()
    serializer_class = VenueSerializer

    def get_permissions(self):
        # Consultar las sedes lo puede hacer cualquier usuario autenticado
        # (por ejemplo, para poblar filtros); crearlas, solo el Administrador.
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsAdministrator()]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Por defecto se listan solo las sedes activas: una sede inactiva no
        # debe aparecer en la selección de sede al crear usuarios o pedidos.
        if self.request.query_params.get("include_inactive") == "true":
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        venue = serializer.save()
        record_event(
            event_type=EventType.VENUE_CREATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Venue",
            entity_id=venue.id,
            description=f"Creación de la sede '{venue.name}'.",
            request=self.request,
        )
