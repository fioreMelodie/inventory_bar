"""
Módulo 5 - Gestión de Proveedores.

Directorio de proveedores vinculado al catálogo de productos. El módulo es
únicamente informativo: no genera órdenes de compra, transacciones ni afecta
el inventario (propuesta comercial V1.1, sección 3.2.1.8).
"""
from django.db import models


class Supplier(models.Model):
    """Proveedor que suministra productos del catálogo."""

    name = models.CharField(
        "name",
        max_length=150,
        unique=True,
        help_text="Must be unique in the supplier directory.",
    )
    phone = models.CharField("contact phone", max_length=40, blank=True)
    email = models.EmailField("email address", max_length=254, blank=True)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "supplier"
        verbose_name_plural = "suppliers"
        ordering = ["name"]

    def __str__(self):
        return self.name
