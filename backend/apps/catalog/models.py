"""
Módulo 4 - Catálogo de Productos.

El catálogo es único y compartido por todas las sedes: los atributos y los
precios son iguales en todas ellas. Lo que varía por sede es el stock, que se
gestiona en el módulo de Inventario.

Solo se contemplan productos físicos: no hay servicios, combos, promociones ni
fechas de vencimiento (propuesta comercial V1.1, sección 3.2.1.2).
"""
from django.db import models


class Product(models.Model):
    """Producto del catálogo global."""

    name = models.CharField(
        "nombre",
        max_length=150,
        unique=True,
        help_text="Debe ser único en el catálogo.",
    )
    product_type = models.CharField("tipo", max_length=80)
    category = models.CharField("categoría", max_length=80)

    # Los valores se manejan en pesos colombianos sin decimales, en números
    # enteros positivos.
    purchase_price = models.PositiveIntegerField("valor de compra")
    sale_price = models.PositiveIntegerField("valor de venta")

    # Un producto tiene un único proveedor principal; un proveedor puede
    # suministrar varios productos. La relación es informativa: no genera
    # órdenes de compra automáticas (HU13).
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="proveedor",
    )

    image = models.ImageField(
        "imagen", upload_to="products/", blank=True, null=True
    )

    # Un producto inactivo se retira del catálogo sin eliminarlo: no aparece en
    # pedidos ni en el catálogo de meseros, pero su histórico se conserva.
    is_active = models.BooleanField("activo", default=True)

    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("última modificación", auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["product_type"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return self.name
