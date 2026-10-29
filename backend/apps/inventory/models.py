"""
Módulo 6 - Gestión de Inventario.

Aunque el catálogo de productos es compartido, cada sede mantiene su propio
nivel de inventario. El stock se maneja siempre en unidades enteras: no se
admiten fracciones ni unidades de volumen (ml, litros, gramos).
"""
from django.conf import settings
from django.db import models


class Stock(models.Model):
    """Existencias de un producto en una sede concreta."""

    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.CASCADE,
        related_name="stock_items",
        verbose_name="venue",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stock_items",
        verbose_name="product",
    )
    quantity = models.PositiveIntegerField("available quantity", default=0)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "stock item"
        verbose_name_plural = "stock items"
        ordering = ["product__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["venue", "product"], name="unique_stock_per_venue_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} at {self.venue.name}: {self.quantity}"


class MovementType(models.TextChoices):
    """Origen de un movimiento de inventario."""

    ENTRY = "ENTRY", "Stock entry"
    ORDER_DISCOUNT = "ORDER_DISCOUNT", "Order stock deduction"
    ORDER_RESTORE = "ORDER_RESTORE", "Cancelled order stock restoration"


class StockMovement(models.Model):
    """
    Movimiento de inventario.

    Deja trazabilidad de cada variación del stock: quién la hizo, en qué sede,
    sobre qué producto y con qué cantidad. Los movimientos no se modifican ni
    se eliminan.
    """

    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="venue",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="stock_movements",
        verbose_name="product",
    )
    movement_type = models.CharField(
        "movement type", max_length=20, choices=MovementType.choices
    )
    # Positiva en las entradas y negativa en las salidas, de modo que la suma
    # de los movimientos reconstruye el stock actual.
    quantity = models.IntegerField("quantity")
    # Los movimientos originados por un pedido guardan su referencia, de modo
    # que el consumo sea trazable hasta la orden que lo produjo.
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="order",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stock_movements",
        verbose_name="recorded by",
    )
    created_at = models.DateTimeField("date and time", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "stock movement"
        verbose_name_plural = "stock movements"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} of {self.quantity} "
            f"{self.product.name} at {self.venue.name}"
        )
