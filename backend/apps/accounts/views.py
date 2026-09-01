"""
Vistas del Módulo 3 - Administración de Usuarios.

HU06: Crear usuario con rol y sede asignada.
"""
from rest_framework import mixins, viewsets

from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import User
from .permissions import IsAdministrator
from .serializers import UserCreateSerializer, UserSerializer


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Cuentas de usuario del sistema.

    - POST /api/users/  crea una cuenta (HU06).
    - GET  /api/users/  lista las cuentas registradas.

    Toda la gestión de cuentas es exclusiva del Administrador: no existe
    autoregistro en el sistema.
    """

    queryset = User.objects.select_related("venue").all()
    permission_classes = [IsAdministrator]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Por defecto se listan solo las cuentas activas; las inactivas se
        # consultan explícitamente para revisar el historial.
        if self.request.query_params.get("include_inactive") != "true":
            queryset = queryset.filter(is_active=True)

        venue_id = self.request.query_params.get("venue")
        if venue_id:
            queryset = queryset.filter(venue_id=venue_id)

        return queryset

    def perform_create(self, serializer):
        user = serializer.save()
        sede = user.venue.name if user.venue else "sin sede asignada"
        record_event(
            event_type=EventType.USER_CREATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="User",
            entity_id=user.id,
            description=(
                f"Creación del usuario '{user.username}' con rol "
                f"{user.get_role_display()} y sede {sede}."
            ),
            request=self.request,
        )
