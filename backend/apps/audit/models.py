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

    LOGIN_SUCCESS = "LOGIN_SUCCESS", "Successful sign-in"
    LOGIN_FAILED = "LOGIN_FAILED", "Failed sign-in"
    LOGIN_BLOCKED = "LOGIN_BLOCKED", "Sign-in locked after failed attempts"
    SESSION_TIMEOUT = "SESSION_TIMEOUT", "Inactivity sign-out"
    SESSION_LOGOUT = "SESSION_LOGOUT", "Manual sign-out"
    SESSION_DISCONNECTED = "SESSION_DISCONNECTED", "Connection loss sign-out"
    SESSION_REVOKED = "SESSION_REVOKED", "Session revoked"
    VENUE_CREATED = "VENUE_CREATED", "Venue created"
    VENUE_UPDATED = "VENUE_UPDATED", "Venue updated"
    VENUE_DEACTIVATED = "VENUE_DEACTIVATED", "Venue deactivated"
    USER_CREATED = "USER_CREATED", "User created"
    USER_UPDATED = "USER_UPDATED", "User updated"
    USER_DEACTIVATED = "USER_DEACTIVATED", "User deactivated"
    USER_REACTIVATED = "USER_REACTIVATED", "User reactivated"
    PRODUCT_CREATED = "PRODUCT_CREATED", "Product created"
    PRODUCT_UPDATED = "PRODUCT_UPDATED", "Product updated"
    SUPPLIER_CREATED = "SUPPLIER_CREATED", "Supplier created"
    SUPPLIER_UPDATED = "SUPPLIER_UPDATED", "Supplier updated"
    SUPPLIER_DELETED = "SUPPLIER_DELETED", "Supplier deleted"
    SUPPLIER_PRODUCTS_LINKED = "SUPPLIER_PRODUCTS_LINKED", "Supplier products linked"
    STOCK_ENTRY = "STOCK_ENTRY", "Stock entry"
    TABLE_CREATED = "TABLE_CREATED", "Table created"
    TABLE_UPDATED = "TABLE_UPDATED", "Table updated"
    TABLE_DEACTIVATED = "TABLE_DEACTIVATED", "Table deactivated"
    ORDER_OPENED = "ORDER_OPENED", "Order opened"
    ORDER_CANCELLED = "ORDER_CANCELLED", "Order cancelled"
    ORDER_ITEM_ADDED = "ORDER_ITEM_ADDED", "Order item added"
    ORDER_SENT_TO_CASHIER = "ORDER_SENT_TO_CASHIER", "Order sent to cashier"
    STOCK_DISCOUNT = "STOCK_DISCOUNT", "Order stock deducted"
    STOCK_RESTORE = "STOCK_RESTORE", "Cancelled order stock restored"
    PAYMENT_PROCESSED = "PAYMENT_PROCESSED", "Payment processed"
    INVOICE_GENERATED = "INVOICE_GENERATED", "Receipt generated"


class AuditEventQuerySet(models.QuerySet):
    """QuerySet que impide la modificación masiva de registros de auditoría."""

    def update(self, **kwargs):
        raise NotImplementedError("Audit records are immutable.")

    def delete(self):
        raise NotImplementedError("Audit records cannot be deleted.")


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
        verbose_name="user",
    )
    # Se conserva el nombre de usuario en texto para que el registro siga siendo
    # legible aunque la cuenta sea eliminada o el intento corresponda a un
    # usuario inexistente.
    username = models.CharField("username", max_length=150)
    event_type = models.CharField("event type", max_length=40, choices=EventType.choices)
    entity = models.CharField("entity", max_length=60, blank=True)
    entity_id = models.CharField("entity ID", max_length=40, blank=True)
    description = models.TextField("description", blank=True)
    ip_address = models.GenericIPAddressField("IP address", null=True, blank=True)
    venue = models.ForeignKey("locations.Venue", on_delete=models.PROTECT, null=True, blank=True,
                              related_name="audit_events", verbose_name="venue")
    venue_name = models.CharField("recorded venue name", max_length=120, blank=True, default="")
    venue_recorded = models.BooleanField("venue context recorded", default=False)
    created_at = models.DateTimeField("date and time", auto_now_add=True, db_index=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        verbose_name = "audit event"
        verbose_name_plural = "audit events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at", "id"], name="audit_date_id_idx"),
            models.Index(fields=["venue", "created_at", "id"], name="audit_venue_date_idx"),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["username"]),
        ]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {self.username} - {self.event_type}"

    def save(self, *args, **kwargs):
        """Permite la creación pero nunca la modificación de un registro."""
        if self.pk is not None:
            raise NotImplementedError("Audit records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Audit records cannot be deleted.")
