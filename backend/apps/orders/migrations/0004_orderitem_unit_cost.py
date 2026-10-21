"""
Incorpora el valor de compra congelado en cada ítem de pedido.

Los ítems ya existentes se completan con el valor de compra actual de su
producto: es la mejor aproximación disponible, porque el costo histórico no se
guardaba antes de esta migración.
"""
from django.db import migrations, models


def backfill_unit_cost(apps, schema_editor):
    OrderItem = apps.get_model("orders", "OrderItem")

    for item in OrderItem.objects.select_related("product").iterator():
        if item.unit_cost == 0:
            item.unit_cost = item.product.purchase_price
            item.save(update_fields=["unit_cost"])


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_order_paid_at_alter_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="unit_cost",
            field=models.PositiveIntegerField(
                default=0, verbose_name="valor de compra unitario"
            ),
        ),
        migrations.RunPython(backfill_unit_cost, migrations.RunPython.noop),
    ]
