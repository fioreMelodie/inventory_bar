"""
Módulo de Auditoría y Trazabilidad.

Registra de forma inmutable cada acción relevante del sistema (inicio de sesión,
pedido, pago, cambio de inventario). Requisito transversal de la propuesta
comercial V1.1: "Los registros de auditoría son inmutables; ningún perfil puede
modificarlos ni eliminarlos".
"""
from django.conf import settings
from django.db import models


class EventType(models.TextChoices):
    """Tipos de evento registrables en el log de auditoría."""

    LOGIN_SUCCESS = "LOGIN_SUCCESS", "Inicio de sesión exitoso"
    LOGIN_FAILED = "LOGIN_FAILED", "Intento de inicio de sesión fallido"
    LOGIN_BLOCKED = "LOGIN_BLOCKED", "Acceso bloqueado por intentos fallidos"


class AuditEventQuerySet(models.QuerySet):
    """QuerySet que impide la modificación masiva de registros de auditoría."""

    def update(self, **kwargs):
        raise NotImplementedError("Los registros de auditoría son inmutables.")

    def delete(self):
        raise NotImplementedError("Los registros de auditoría no pueden eliminarse.")


class AuditEvent(models.Model):
    """
    Registro inmutable de un evento del sistema.

    Cada registro incluye usuario, tipo de evento, entidad afectada, sede, fecha
    y hora exacta, según lo exigido en la sección 3.2.1.9 de la propuesta.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        verbose_name="usuario",
    )
    # Se conserva el nombre de usuario en texto para que el registro siga siendo
    # legible aunque la cuenta sea eliminada o el intento corresponda a un
    # usuario inexistente.
    username = models.CharField("nombre de usuario", max_length=150)
    event_type = models.CharField("tipo de evento", max_length=40, choices=EventType.choices)
    entity = models.CharField("entidad afectada", max_length=60, blank=True)
    entity_id = models.CharField("id de la entidad", max_length=40, blank=True)
    description = models.TextField("descripción", blank=True)
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True, db_index=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["username"]),
        ]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {self.username} - {self.event_type}"

    def save(self, *args, **kwargs):
        """Permite la creación pero nunca la modificación de un registro."""
        if self.pk is not None:
            raise NotImplementedError("Los registros de auditoría son inmutables.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Los registros de auditoría no pueden eliminarse.")
