"""
Módulo 7 - Gestión de Mesas.

Cada sede configura sus propias mesas, sin límite de cantidad. El estado de la
mesa se actualiza automáticamente a partir de los pedidos: una mesa con pedido
activo está OCUPADA y vuelve a LIBRE cuando se registra el pago.
"""
from django.db import models


class TableStatus(models.TextChoices):
    """Estado operativo de una mesa."""

    FREE = "FREE", "Free"
    OCCUPIED = "OCCUPIED", "Occupied"


class Table(models.Model):
    """Mesa de una sede."""

    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.PROTECT,
        related_name="tables",
        verbose_name="venue",
    )
    # El identificador es único dentro de la sede: puede existir "Mesa 1" en
    # Galería y "Mesa 1" en Zona T.
    identifier = models.CharField("identifier", max_length=40)

    status = models.CharField(
        "status", max_length=20, choices=TableStatus.choices, default=TableStatus.FREE
    )

    # Las mesas no se eliminan cuando tienen histórico de pedidos: se inactivan
    # para conservar la trazabilidad.
    is_active = models.BooleanField("active", default=True)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "table"
        verbose_name_plural = "tables"
        ordering = ["venue__name", "identifier"]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "identifier"], name="unique_table_identifier_per_venue"
            )
        ]

    def __str__(self):
        return f"{self.identifier} ({self.venue.name})"

    @property
    def is_free(self):
        return self.status == TableStatus.FREE
