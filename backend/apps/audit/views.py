"""
Vistas del Módulo 11 - Auditoría y Trazabilidad.

HU30: Consultar el log de eventos del sistema.
"""
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdministrator

from .models import AuditEvent, EventType
from .serializers import AuditEventSerializer


class AuditEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Log de eventos del sistema.

    - GET /api/audit/events/        consulta el log con filtros (HU30).
    - GET /api/audit/event-types/   tipos de evento disponibles.

    Solo el Administrador accede al módulo. El log es inmutable: el conjunto
    de vistas no expone escritura y el propio modelo impide modificar o
    eliminar registros.
    """

    queryset = AuditEvent.objects.select_related("user", "venue")
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdministrator]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Los filtros son aditivos.
        date_from = parse_date(self.request.query_params.get("date_from", ""))
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = parse_date(self.request.query_params.get("date_to", ""))
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        username = self.request.query_params.get("username")
        if username:
            queryset = queryset.filter(username__icontains=username.strip())

        event_type = self.request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        venue_id = self.request.query_params.get("venue")
        if venue_id:
            queryset = queryset.filter(venue_id=venue_id)

        return queryset

    def list(self, request, *args, **kwargs):
        """Valida el rango de fechas antes de construir el listado."""
        date_from = parse_date(request.query_params.get("date_from", ""))
        date_to = parse_date(request.query_params.get("date_to", ""))

        if date_from and date_to and date_from > date_to:
            return Response(
                {"detail": "The start date cannot be later than the end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"], url_path="event-types")
    def event_types(self, request):
        """Tipos de evento registrables, para poblar el filtro."""
        return Response(
            [{"value": value, "label": label} for value, label in EventType.choices]
        )
