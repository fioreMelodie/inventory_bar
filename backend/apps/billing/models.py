"""
Módulo 9 - Pagos y Facturación.

Cada pago exitoso genera una factura. Las facturas son el soporte documental
de la transacción: no pueden modificarse ni anularse bajo ningún perfil
(propuesta comercial V1.1, sección 3.2.1.6).
"""
from django.conf import settings
from django.db import models


class PaymentMethod(models.TextChoices):
    """Métodos de pago aceptados. No se contempla pasarela de pago."""

    CASH = "CASH", "Efectivo"


class InvoiceQuerySet(models.QuerySet):
    """QuerySet que impide la modificación masiva de facturas."""

    def update(self, **kwargs):
        raise NotImplementedError("Las facturas no pueden modificarse.")

    def delete(self):
        raise NotImplementedError("Las facturas no pueden eliminarse.")


class Invoice(models.Model):
    """Factura generada al completar el pago de un pedido."""

    # Número visible al usuario, único en todo el sistema y secuencial dentro
    # de cada sede (criterio de la HU25).
    number = models.CharField("número", max_length=30, unique=True)
    sequence = models.PositiveIntegerField("consecutivo de la sede")

    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="sede",
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="invoice",
        verbose_name="pedido",
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="cajero",
    )

    payment_method = models.CharField(
        "método de pago", max_length=20, choices=PaymentMethod.choices
    )
    total = models.PositiveIntegerField("total")

    # Solo aplican al pago en efectivo.
    amount_received = models.PositiveIntegerField(
        "monto recibido", null=True, blank=True
    )
    change_given = models.PositiveIntegerField("cambio entregado", default=0)

    created_at = models.DateTimeField("fecha y hora", auto_now_add=True, db_index=True)

    objects = InvoiceQuerySet.as_manager()

    class Meta:
        verbose_name = "factura"
        verbose_name_plural = "facturas"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "sequence"], name="unique_invoice_sequence_per_venue"
            )
        ]

    def __str__(self):
        return f"{self.number} - {self.venue.name} - {self.total}"

    def save(self, *args, **kwargs):
        """Permite la creación pero nunca la modificación de la factura."""
        if self.pk is not None:
            raise NotImplementedError("Las facturas no pueden modificarse.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Las facturas no pueden eliminarse.")
