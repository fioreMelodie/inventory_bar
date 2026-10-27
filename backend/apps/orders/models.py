"""
Módulo 8 - Gestión de Pedidos.

El pedido se asocia directamente a una mesa. Una mesa ocupada tiene un único
pedido activo. Los pedidos no se eliminan: quedan registrados de forma
permanente para fines de auditoría y reportes.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class OrderStatus(models.TextChoices):
    """Estados por los que pasa un pedido."""

    OPEN = "OPEN", "Abierto"
    IN_CASHIER = "IN_CASHIER", "En caja"
    PAID = "PAID", "Pagado"
    CANCELLED = "CANCELLED", "Cancelado"


class Order(models.Model):
    """Pedido de una mesa."""

    venue = models.ForeignKey(
        "locations.Venue",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="sede",
    )
    table = models.ForeignKey(
        "tables.Table",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="mesa",
    )
    waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="mesero",
    )

    status = models.CharField(
        "estado", max_length=20, choices=OrderStatus.choices, default=OrderStatus.OPEN
    )

    # El total se mantiene calculado a partir de los ítems del pedido.
    total = models.PositiveIntegerField("total", default=0)

    opened_at = models.DateTimeField("fecha y hora de apertura", default=timezone.now)
    sent_to_cashier_at = models.DateTimeField(
        "fecha y hora de envío a caja", null=True, blank=True
    )
    paid_at = models.DateTimeField("fecha y hora del pago", null=True, blank=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-opened_at"]
        indexes = [
            # El reporte de ventas filtra por estado y fecha de pago; sin este
            # índice la consulta recorrería toda la tabla de pedidos (HU29).
            models.Index(fields=["status", "paid_at"], name="order_status_paid_idx"),
        ]
        constraints = [
            # Una mesa ocupada solo puede tener un pedido activo a la vez.
            models.UniqueConstraint(
                fields=["table"],
                condition=models.Q(status="OPEN"),
                name="unique_open_order_per_table",
            )
        ]

    def __str__(self):
        return f"Pedido {self.id} - {self.table.identifier} ({self.get_status_display()})"

    @property
    def is_open(self):
        """Solo los pedidos abiertos admiten modificaciones."""
        return self.status == OrderStatus.OPEN

    def recalculate_total(self):
        """
        Recalcula el total a partir de los ítems registrados.

        La suma se hace en la base de datos y no sobre `self.items.all()`:
        cuando la instancia llega de un queryset con prefetch_related, esa
        relación está cacheada y devolvería los ítems anteriores al cambio.
        """
        self.total = self.items.aggregate(
            total=models.Sum(models.F("quantity") * models.F("unit_price"))
        )["total"] or 0
        self.save(update_fields=["total"])
        return self.total


class OrderItem(models.Model):
    """
    Producto solicitado dentro de un pedido.

    El precio unitario se copia del catálogo en el momento de agregar el ítem:
    un cambio posterior de precio no altera los pedidos ya registrados
    (criterio de la HU10).
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="pedido",
    )
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="producto",
    )
    quantity = models.PositiveIntegerField("cantidad")
    unit_price = models.PositiveIntegerField("precio unitario")
    # El valor de compra también se congela: el reporte de ventas calcula la
    # ganancia con el costo vigente al momento de la venta, no con el actual
    # del catálogo (HU27).
    unit_cost = models.PositiveIntegerField("valor de compra unitario", default=0)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True)

    class Meta:
        verbose_name = "ítem de pedido"
        verbose_name_plural = "ítems de pedido"
        ordering = ["created_at"]
        constraints = [
            # Un producto aparece una sola vez por pedido: las cantidades se
            # acumulan sobre el mismo ítem (criterio de la HU20).
            models.UniqueConstraint(
                fields=["order", "product"], name="unique_product_per_order"
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (pedido {self.order_id})"

    @property
    def subtotal(self):
        """Importe de la línea: cantidad por precio unitario."""
        return self.quantity * self.unit_price

    @property
    def cost_total(self):
        """Costo de la línea: cantidad por valor de compra unitario."""
        return self.quantity * self.unit_cost

    @property
    def profit(self):
        """Ganancia de la línea: venta menos costo."""
        return self.subtotal - self.cost_total
