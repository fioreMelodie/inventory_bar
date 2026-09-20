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
        "nombre",
        max_length=150,
        unique=True,
        help_text="Debe ser único en el directorio de proveedores.",
    )
    phone = models.CharField("teléfono de contacto", max_length=40, blank=True)
    email = models.EmailField("correo electrónico", max_length=254, blank=True)

    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("última modificación", auto_now=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["name"]

    def __str__(self):
        return self.name
