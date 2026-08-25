"""
Reglas de negocio de autenticación.

Política de bloqueo (backlog del producto, HU01): tras 3 intentos fallidos
consecutivos el acceso se bloquea durante 5 minutos y se notifica al usuario.
"""
from datetime import timedelta

from django.utils import timezone

from .models import LoginAttempt

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_DURATION = timedelta(minutes=5)


def get_lockout_remaining(username):
    """
    Devuelve los segundos restantes de bloqueo para un usuario.

    Retorna 0 si la cuenta no está bloqueada. Se consideran únicamente los
    intentos posteriores al último inicio de sesión exitoso, de modo que un
    acceso correcto reinicia el contador.
    """
    last_success = (
        LoginAttempt.objects.filter(username=username, successful=True)
        .order_by("-created_at")
        .first()
    )

    failures = LoginAttempt.objects.filter(username=username, successful=False)
    if last_success:
        failures = failures.filter(created_at__gt=last_success.created_at)

    recent_failures = list(failures.order_by("-created_at")[:MAX_FAILED_ATTEMPTS])
    if len(recent_failures) < MAX_FAILED_ATTEMPTS:
        return 0

    unlocks_at = recent_failures[0].created_at + LOCKOUT_DURATION
    remaining = (unlocks_at - timezone.now()).total_seconds()
    return max(0, int(remaining))


def register_attempt(username, successful, ip_address=None):
    """Deja constancia de un intento de inicio de sesión."""
    return LoginAttempt.objects.create(
        username=username,
        successful=successful,
        ip_address=ip_address,
    )
