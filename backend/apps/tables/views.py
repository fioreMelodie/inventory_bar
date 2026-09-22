"""
Vistas del Módulo 7 - Gestión de Mesas.

HU17: Crear y configurar mesas por sede.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import Table, TableStatus
from .serializers import TableSerializer


class TableViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Mesas de cada sede.

    - POST  /api/tables/                 crea una mesa (solo Administrador).
    - GET   /api/tables/                 lista las mesas de la sede.
    - PATCH /api/tables/{id}/            edita el identificador.
    - POST  /api/tables/{id}/deactivate/ inactiva la mesa.

    No hay límite de mesas por sede. Las mesas no se eliminan: se inactivan,
    para conservar el histórico de pedidos.
    """

    queryset = Table.objects.select_related("venue").all()
    serializer_class = TableSerializer

    def get_permissions(self):
        # Consultar las mesas lo necesitan los tres roles (vista de sala);
        # crearlas y configurarlas es exclusivo del Administrador.
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsAdministrator()]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action not in ("list",):
            return queryset

        # Cajero y Mesero solo ven las mesas de su sede asignada.
        if self.request.user.role != Role.ADMIN:
            queryset = queryset.filter(venue=self.request.user.venue)
        else:
            venue_id = self.request.query_params.get("venue")
            if venue_id:
                queryset = queryset.filter(venue_id=venue_id)

        if self.request.query_params.get("include_inactive") != "true":
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_create(self, serializer):
        # Las mesas se crean siempre con estado LIBRE.
        table = serializer.save(status=TableStatus.FREE)
        record_event(
            event_type=EventType.TABLE_CREATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Table",
            entity_id=table.id,
            description=(
                f"Creación de la mesa '{table.identifier}' en la sede "
                f"'{table.venue.name}'."
            ),
            request=self.request,
        )

    def perform_update(self, serializer):
        table = serializer.instance
        previous_identifier = table.identifier

        table = serializer.save()

        record_event(
            event_type=EventType.TABLE_UPDATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Table",
            entity_id=table.id,
            description=(
                f"Edición de la mesa en la sede '{table.venue.name}'. "
                f"identifier: '{previous_identifier}' -> '{table.identifier}'."
            ),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """
        Inactiva la mesa.

        No se admite eliminar mesas: el histórico de pedidos debe conservarse.
        Una mesa ocupada no puede inactivarse mientras tenga el pedido activo.
        """
        table = self.get_object()

        if not table.is_active:
            return Response(
                {"detail": "This table is already inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if table.status == TableStatus.OCCUPIED:
            return Response(
                {"detail": "This table has an active order and cannot be deactivated."},
                status=status.HTTP_409_CONFLICT,
            )

        table.is_active = False
        table.save(update_fields=["is_active", "updated_at"])

        record_event(
            event_type=EventType.TABLE_DEACTIVATED,
            username=request.user.username,
            user=request.user,
            entity="Table",
            entity_id=table.id,
            description=(
                f"Inactivación de la mesa '{table.identifier}' en la sede "
                f"'{table.venue.name}'."
            ),
            request=request,
        )

        return Response(self.get_serializer(table).data, status=status.HTTP_200_OK)
