"""
Reglas de negocio del Módulo 10 - Reportes.

El reporte de ventas se construye sobre los ítems de pedidos ya PAGADOS: un
pedido abierto o en caja todavía no es una venta.

Los importes se toman de los valores congelados en el ítem, no del catálogo
actual, de modo que un cambio de precio posterior no altere el histórico.
"""
from django.db.models import F, Sum
from django.db.models.functions import TruncDate

from apps.orders.models import OrderItem, OrderStatus


def build_sales_report(*, date_from, date_to, venue=None, product=None, category=None):
    """
    Devuelve las líneas del reporte de ventas agrupadas por día, sede y
    producto, ordenadas por fecha descendente.

    Los filtros son aditivos: cada uno reduce el conjunto de resultados.
    """
    queryset = OrderItem.objects.filter(
        order__status=OrderStatus.PAID,
        order__paid_at__date__gte=date_from,
        order__paid_at__date__lte=date_to,
    )

    if venue is not None:
        queryset = queryset.filter(order__venue=venue)

    if product is not None:
        queryset = queryset.filter(product=product)

    if category:
        queryset = queryset.filter(product__category__iexact=category.strip())

    # Los nombres de los campos agrupados se dejan tal como los expresa el ORM
    # y se traducen después: un alias llamado `product_id` chocaría con el
    # campo del propio modelo.
    rows = (
        queryset.annotate(sale_date=TruncDate("order__paid_at"))
        .values(
            "sale_date",
            "order__venue_id",
            "order__venue__name",
            "product_id",
            "product__name",
            "product__category",
        )
        .annotate(
            # El alias no puede llamarse `quantity`: taparía el campo del
            # modelo que usan las dos sumas siguientes.
            quantity_sold=Sum("quantity"),
            sale_value=Sum(F("quantity") * F("unit_price")),
            purchase_value=Sum(F("quantity") * F("unit_cost")),
        )
        .order_by("-sale_date", "order__venue__name", "product__name")
    )

    return [
        {
            "date": row["sale_date"],
            "venue": row["order__venue_id"],
            "venue_name": row["order__venue__name"],
            "product": row["product_id"],
            "product_name": row["product__name"],
            "category": row["product__category"],
            "quantity": row["quantity_sold"],
            "sale_value": row["sale_value"],
            "purchase_value": row["purchase_value"],
            # La ganancia se deriva de los dos importes ya agregados.
            "profit": row["sale_value"] - row["purchase_value"],
        }
        for row in rows
    ]


def summarize(rows):
    """Totaliza las líneas del reporte."""
    return {
        "quantity": sum(row["quantity"] for row in rows),
        "sale_value": sum(row["sale_value"] for row in rows),
        "purchase_value": sum(row["purchase_value"] for row in rows),
        "profit": sum(row["profit"] for row in rows),
    }
