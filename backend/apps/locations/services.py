"""
Reglas de negocio del Módulo 2 - Administración de Sedes.

Concentra las validaciones de inactivación y los efectos colaterales sobre los
usuarios asignados a la sede.
"""
from apps.audit.models import EventType
from apps.audit.services import record_event

# Una sede no puede inactivarse si tiene operación en curso. Los módulos que
# introducen operación (mesas y pedidos, HU17 a HU21) registran aquí su propia
# verificación mediante register_deactivation_guard.
#
# Cada guarda es un invocable que recibe la sede y devuelve un mensaje de error
# si la inactivación no debe permitirse, o None si no hay impedimento.
_DEACTIVATION_GUARDS = []


def register_deactivation_guard(guard):
    """Registra una verificación previa a la inactivación de una sede."""
    _DEACTIVATION_GUARDS.append(guard)
    return guard


def get_deactivation_blocker(venue):
    """
    Devuelve el motivo por el que la sede no puede inactivarse, o None.

    Criterio de aceptación de la HU05: no se puede inactivar una sede si tiene
    mesas con pedidos en estado ABIERTO.
    """
    for guard in _DEACTIVATION_GUARDS:
        message = guard(venue)
        if message:
            return message
    return None


def deactivate_venue(venue, *, performed_by, request=None):
    """
    Inactiva una sede y libera la asignación de sus usuarios.

    Los usuarios de la sede quedan sin sede asignada y requieren reasignación.
    El historial de transacciones, reportes y auditoría se conserva íntegro.
    """
    venue.is_active = False
    venue.save(update_fields=["is_active", "updated_at"])

    affected_users = list(venue.users.all())
    for user in affected_users:
        user.venue = None
        user.save(update_fields=["venue", "updated_at"])

    description = f"Inactivación de la sede '{venue.name}'."
    if affected_users:
        usernames = ", ".join(user.username for user in affected_users)
        description += f" Usuarios que quedan sin sede asignada: {usernames}."

    record_event(
        event_type=EventType.VENUE_DEACTIVATED,
        username=performed_by.username,
        user=performed_by,
        entity="Venue",
        entity_id=venue.id,
        description=description,
        request=request,
    )
    return venue
