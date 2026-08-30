"""
Vistas del Módulo 2 - Administración de Sedes.

HU04: Crear sede.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import Venue
from .serializers import VenueDeactivationSerializer, VenueSerializer
from .services import deactivate_venue, get_deactivation_blocker


class VenueViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Sedes del negocio.

    - POST  /api/venues/                  crea una sede (HU04).
    - GET   /api/venues/                  lista las sedes disponibles.
    - PATCH /api/venues/{id}/             edita nombre y dirección (HU05).
    - POST  /api/venues/{id}/deactivate/  inactiva la sede (HU05).

    Todas las operaciones de escritura son exclusivas del Administrador.
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
        # Las acciones de escritura deben poder alcanzar cualquier sede, aunque
        # esté inactiva.
        if self.action not in ("list",):
            return queryset
        if self.request.query_params.get("include_inactive") == "true":
            return queryset
        return queryset.filter(is_active=True)

    def perform_update(self, serializer):
        """Edición de la sede: se registra qué cambió y con qué valores."""
        venue = serializer.instance
        previous = {"name": venue.name, "address": venue.address}

        venue = serializer.save()

        cambios = [
            f"{campo}: '{valor_anterior}' -> '{getattr(venue, campo)}'"
            for campo, valor_anterior in previous.items()
            if valor_anterior != getattr(venue, campo)
        ]
        record_event(
            event_type=EventType.VENUE_UPDATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Venue",
            entity_id=venue.id,
            description=(
                f"Edición de la sede '{venue.name}'. " + "; ".join(cambios)
                if cambios
                else f"Edición de la sede '{venue.name}' sin cambios efectivos."
            ),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """
        Inactiva la sede.

        Requiere confirmación explícita del Administrador y verifica que la
        sede no tenga operación en curso. El historial de la sede se conserva.
        """
        venue = self.get_object()

        serializer = VenueDeactivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not venue.is_active:
            return Response(
                {"detail": "This venue is already inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blocker = get_deactivation_blocker(venue)
        if blocker:
            return Response({"detail": blocker}, status=status.HTTP_409_CONFLICT)

        deactivate_venue(venue, performed_by=request.user, request=request)
        return Response(self.get_serializer(venue).data, status=status.HTTP_200_OK)

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
