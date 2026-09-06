"""
Vistas del Módulo 3 - Administración de Usuarios.

HU06: Crear usuario con rol y sede asignada.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import EventType
from apps.audit.services import record_event
from apps.authentication.models import UserSession
from apps.authentication.session_services import close_active_sessions

from .models import User
from .permissions import IsAdministrator
from .serializers import (
    UserCreateSerializer,
    UserSerializer,
    UserStatusChangeSerializer,
    UserUpdateSerializer,
)


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Cuentas de usuario del sistema.

    - POST  /api/users/       crea una cuenta (HU06).
    - GET   /api/users/       lista las cuentas registradas.
    - PATCH /api/users/{id}/             edita una cuenta existente (HU07).
    - POST  /api/users/{id}/deactivate/  inactiva una cuenta (HU08).
    - POST  /api/users/{id}/activate/    reactiva una cuenta inactiva (HU08).

    Toda la gestión de cuentas es exclusiva del Administrador: no existe
    autoregistro en el sistema.
    """

    queryset = User.objects.select_related("venue").all()
    permission_classes = [IsAdministrator]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Las acciones de escritura deben poder alcanzar cualquier cuenta,
        # incluidas las inactivas (por ejemplo, para reactivarlas).
        if self.action not in ("list",):
            return queryset

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

    def perform_update(self, serializer):
        """
        Edición de la cuenta.

        La auditoría registra el campo modificado, su valor anterior y el
        nuevo. El cambio de sede no altera el historial de transacciones
        previas del usuario, y los cambios de rol y sede se aplican a partir
        del siguiente inicio de sesión, porque la sesión activa conserva los
        valores con los que se creó.
        """
        user = serializer.instance
        tracked_fields = ("username", "full_name", "role", "venue")
        previous = {field: getattr(user, field) for field in tracked_fields}
        password_changed = bool(serializer.validated_data.get("password"))

        user = serializer.save()

        changes = [
            f"{field}: '{previous[field]}' -> '{getattr(user, field)}'"
            for field in tracked_fields
            if previous[field] != getattr(user, field)
        ]
        if password_changed:
            # Nunca se registra el valor de la contraseña, solo el hecho.
            changes.append("password: actualizada")

        record_event(
            event_type=EventType.USER_UPDATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="User",
            entity_id=user.id,
            description=(
                f"Edición del usuario '{user.username}'. " + "; ".join(changes)
                if changes
                else f"Edición del usuario '{user.username}' sin cambios efectivos."
            ),
            request=self.request,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """
        Inactiva una cuenta de usuario.

        La cuenta deja de poder autenticarse y su sesión activa, si la tiene,
        se invalida de inmediato. El historial de pedidos, pagos y auditoría
        del usuario permanece íntegro, y sus pedidos ABIERTOS se mantienen en
        ese estado para que otro usuario los gestione.
        """
        user = self.get_object()

        serializer = UserStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"detail": "This user is already inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

        closed = close_active_sessions(
            user, UserSession.ClosingReason.USER_DEACTIVATED, request=request
        )

        record_event(
            event_type=EventType.USER_DEACTIVATED,
            username=request.user.username,
            user=request.user,
            entity="User",
            entity_id=user.id,
            description=(
                f"Inactivación del usuario '{user.username}'. "
                f"Sesiones activas invalidadas: {len(closed)}."
            ),
            request=request,
        )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Reactiva una cuenta inactiva. Solo el Administrador puede hacerlo."""
        user = self.get_object()

        serializer = UserStatusChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if user.is_active:
            return Response(
                {"detail": "This user is already active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])

        record_event(
            event_type=EventType.USER_REACTIVATED,
            username=request.user.username,
            user=request.user,
            entity="User",
            entity_id=user.id,
            description=f"Reactivación del usuario '{user.username}'.",
            request=request,
        )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
