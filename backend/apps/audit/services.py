"""Servicios del módulo de auditoría."""
from .models import AuditEvent


def get_client_ip(request):
    """Obtiene la IP del cliente considerando un posible proxy inverso."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_event(*, event_type, username, user=None, entity="", entity_id="",
                 description="", venue=None, request=None):
    """
    Crea un registro de auditoría.

    Punto de entrada único para el log de eventos: cualquier módulo del sistema
    debe registrar sus acciones relevantes a través de esta función.

    Si no se indica la sede, se usa la del usuario que realiza la acción. Las
    acciones del Administrador sobre la parametrización global quedan sin sede,
    porque no pertenecen a ninguna.
    """
    if venue is None and user is not None:
        venue = getattr(user, "venue", None)

    return AuditEvent.objects.create(
        user=user,
        username=username,
        event_type=event_type,
        entity=entity,
        entity_id=str(entity_id) if entity_id else "",
        description=description,
        venue=venue,
        ip_address=get_client_ip(request) if request is not None else None,
    )
