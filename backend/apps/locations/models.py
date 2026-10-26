"""
Módulo 2 - Administración de Sedes.

Cada sede es una unidad operativa independiente: mantiene su propio inventario,
sus mesas y sus usuarios asignados. El catálogo de productos, en cambio, es
compartido por todas las sedes.
"""
from django.db import models


class Venue(models.Model):
    """Sede del negocio (Galería, Zona T, Modelia, ...)."""

    name = models.CharField(
        "name",
        max_length=120,
        unique=True,
        help_text="Venue names must be unique.",
    )
    address = models.CharField("address", max_length=255, blank=True)

    # Una sede inactiva conserva íntegro su historial, pero deja de estar
    # disponible para nuevas operaciones (HU05).
    is_active = models.BooleanField("active", default=True)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "venue"
        verbose_name_plural = "venues"
        ordering = ["name"]

    def __str__(self):
        return self.name
