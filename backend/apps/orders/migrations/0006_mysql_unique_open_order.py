"""
Regla HU19 en MySQL: una mesa solo puede tener un pedido OPEN a la vez.

El UniqueConstraint condicional del modelo (unique_open_order_per_table) solo
existe en SQLite: MySQL no admite índices parciales y Django lo omite sin
avisar. Esta migración crea en MySQL un índice único funcional equivalente.
En SQLite no hace nada.
"""
from django.db import migrations

INDEX_NAME = "unique_open_order_per_table_mysql"


def create_index(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(
        f"CREATE UNIQUE INDEX {INDEX_NAME} ON orders_order "
        "((CASE WHEN status = 'OPEN' THEN table_id END))"
    )


def drop_index(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    schema_editor.execute(f"DROP INDEX {INDEX_NAME} ON orders_order")


class Migration(migrations.Migration):

    # MySQL no permite DDL dentro de una transacción.
    atomic = False

    dependencies = [
        # Renumerada al integrarla: en develop las migraciones 0003 a 0005 ya
        # estaban ocupadas por el estado PAGADO, el costo congelado del ítem y
        # el índice del reporte de ventas.
        ("orders", "0005_order_order_status_paid_idx"),
    ]

    operations = [
        migrations.RunPython(create_index, drop_index),
    ]
