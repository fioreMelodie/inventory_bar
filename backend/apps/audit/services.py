"""Servicios del módulo de auditoría."""
from .models import AuditEvent


def get_client_ip(request):
    """Obtiene la IP del cliente considerando un posible proxy inverso."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_event(*, event_type, username, user=None, entity="", entity_id="",
                 description="", request=None):
    """
    Crea un registro de auditoría.

    Punto de entrada único para el log de eventos: cualquier módulo del sistema
    debe registrar sus acciones relevantes a través de esta función.
    """
    return AuditEvent.objects.create(
        user=user,
        username=username,
        event_type=event_type,
        entity=entity,
        entity_id=str(entity_id) if entity_id else "",
        description=description,
        ip_address=get_client_ip(request) if request is not None else None,
    )
