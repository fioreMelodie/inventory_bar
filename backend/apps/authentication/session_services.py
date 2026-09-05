"""
Cierre de sesiones del Módulo 1 - Autenticación y Sesión.

El log de auditoría distingue el motivo de cada cierre (criterio de aceptación
de la HU03): inactividad, cierre manual del usuario o pérdida de conexión.
"""
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import UserSession

# Correspondencia entre el motivo de cierre y el evento de auditoría y la
# descripción que queda registrada.
CLOSING_EVENTS = {
    UserSession.ClosingReason.INACTIVITY: (
        EventType.SESSION_TIMEOUT,
        "Cierre automático de sesión tras 3 minutos de inactividad.",
    ),
    UserSession.ClosingReason.MANUAL: (
        EventType.SESSION_LOGOUT,
        "El usuario cerró la sesión manualmente.",
    ),
    UserSession.ClosingReason.DISCONNECTION: (
        EventType.SESSION_DISCONNECTED,
        "Cierre de sesión por pérdida de conexión a internet.",
    ),
    UserSession.ClosingReason.USER_DEACTIVATED: (
        EventType.SESSION_REVOKED,
        "Cierre inmediato de la sesión por inactivación de la cuenta.",
    ),
}


def close_session(session, reason, request=None):
    """
    Cierra una sesión registrando el motivo en el log de auditoría.

    No se modifica ningún dato operativo del usuario: los pedidos abiertos
    permanecen en estado ABIERTO en la base de datos para ser gestionados
    posteriormente (criterio común a las HU02 y HU03).
    """
    if not session.is_active:
        return session

    session.close(reason)
    event_type, description = CLOSING_EVENTS[reason]
    record_event(
        event_type=event_type,
        username=session.user.username,
        user=session.user,
        entity="UserSession",
        entity_id=session.id,
        description=description,
        request=request,
    )
    return session


def close_active_sessions(user, reason, request=None):
    """
    Cierra todas las sesiones abiertas de un usuario.

    Se usa al inactivar una cuenta (HU08): si el usuario tiene una sesión
    activa en ese momento, esta se invalida inmediatamente.
    """
    closed = []
    for session in UserSession.objects.filter(user=user, ended_at__isnull=True):
        closed.append(close_session(session, reason, request=request))
    return closed
