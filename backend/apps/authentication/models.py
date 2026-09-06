"""
Módulo 1 - Autenticación y Sesión.

Registra los intentos de inicio de sesión (para el bloqueo por intentos
fallidos) y las sesiones activas del sistema.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class LoginAttempt(models.Model):
    """
    Intento de inicio de sesión, exitoso o fallido.

    Sustenta la política de bloqueo: tras 3 intentos fallidos consecutivos el
    acceso se bloquea durante 5 minutos.
    """

    username = models.CharField("nombre de usuario", max_length=150, db_index=True)
    successful = models.BooleanField("exitoso", default=False)
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "intento de inicio de sesión"
        verbose_name_plural = "intentos de inicio de sesión"
        ordering = ["-created_at"]

    def __str__(self):
        estado = "exitoso" if self.successful else "fallido"
        return f"{self.username} - {estado} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class UserSession(models.Model):
    """
    Sesión de usuario en el sistema.

    Criterio de aceptación de la HU01: "La sesión registra: usuario, rol, sede
    asignada, fecha y hora de ingreso".
    """

    class ClosingReason(models.TextChoices):
        ACTIVE = "ACTIVE", "Sesión activa"
        INACTIVITY = "INACTIVITY", "Cierre automático por inactividad"
        MANUAL = "MANUAL", "Cierre manual por el usuario"
        DISCONNECTION = "DISCONNECTION", "Cierre por pérdida de conexión"
        USER_DEACTIVATED = "USER_DEACTIVATED", "Cierre por inactivación de la cuenta"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="usuario",
    )
    # El rol se guarda en la sesión porque un cambio posterior de rol solo debe
    # aplicar a partir del siguiente inicio de sesión (criterio de la HU07).
    role = models.CharField("rol", max_length=20)
    # La sede se guarda en la sesión porque un cambio posterior solo debe
    # aplicar a partir del siguiente inicio de sesión (criterio de la HU07).
    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
        verbose_name="sede",
    )
    started_at = models.DateTimeField("fecha y hora de ingreso", default=timezone.now)
    last_activity_at = models.DateTimeField("última actividad", default=timezone.now)
    ended_at = models.DateTimeField("fecha y hora de cierre", null=True, blank=True)
    closing_reason = models.CharField(
        "motivo de cierre",
        max_length=20,
        choices=ClosingReason.choices,
        default=ClosingReason.ACTIVE,
    )
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True)

    class Meta:
        verbose_name = "sesión de usuario"
        verbose_name_plural = "sesiones de usuario"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - {self.started_at:%Y-%m-%d %H:%M:%S}"

    @property
    def is_active(self):
        return self.ended_at is None

    def close(self, reason):
        """Cierra la sesión dejando constancia del motivo."""
        if self.ended_at is not None:
            return self
        self.ended_at = timezone.now()
        self.closing_reason = reason
        self.save(update_fields=["ended_at", "closing_reason"])
        return self
