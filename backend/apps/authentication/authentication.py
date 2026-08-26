"""
Autenticación JWT con control de sesión en servidor.

La HU02 exige que la sesión quede "completamente invalidada en servidor (no
solo frontend)". Por eso no basta con que el token expire: cada petición
autenticada verifica que la sesión asociada siga abierta y que el usuario siga
activo, y aplica el corte por inactividad del lado del servidor.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import UserSession

# Tiempo de inactividad definido en la HU02 y en la propuesta comercial V1.1.
# No es configurable por el usuario.
INACTIVITY_TIMEOUT = timedelta(minutes=3)

SESSION_EXPIRED_MESSAGE = "Your session expired due to inactivity. Please sign in again."
SESSION_CLOSED_MESSAGE = "Your session is no longer valid. Please sign in again."


class SessionAwareJWTAuthentication(JWTAuthentication):
    """JWTAuthentication que además valida el estado de la sesión."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        session_id = validated_token.get("session_id")
        if session_id is None:
            # Token emitido sin sesión asociada: no corresponde a un inicio de
            # sesión válido de la aplicación.
            raise AuthenticationFailed(SESSION_CLOSED_MESSAGE, code="session_not_found")

        session = UserSession.objects.filter(id=session_id, user=user).first()
        if session is None or not session.is_active:
            raise AuthenticationFailed(SESSION_CLOSED_MESSAGE, code="session_closed")

        now = timezone.now()
        if now - session.last_activity_at > INACTIVITY_TIMEOUT:
            # El corte se aplica en servidor aunque el frontend no lo haya
            # solicitado (por ejemplo, si el navegador se cerró abruptamente).
            close_session_by_inactivity(session)
            raise AuthenticationFailed(SESSION_EXPIRED_MESSAGE, code="session_expired")

        # Cada interacción del usuario reinicia el contador de inactividad.
        session.last_activity_at = now
        session.save(update_fields=["last_activity_at"])

        return user


def close_session_by_inactivity(session, request=None):
    """
    Cierra una sesión por inactividad y deja el registro de auditoría.

    Los pedidos abiertos del usuario no se ven afectados: permanecen en estado
    ABIERTO para ser gestionados posteriormente (criterio de la HU02).
    """
    session.close(UserSession.ClosingReason.INACTIVITY)
    record_event(
        event_type=EventType.SESSION_TIMEOUT,
        username=session.user.username,
        user=session.user,
        entity="UserSession",
        entity_id=session.id,
        description="Cierre automático de sesión tras 3 minutos de inactividad.",
        request=request,
    )
    return session
