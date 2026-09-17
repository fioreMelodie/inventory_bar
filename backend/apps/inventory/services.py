"""
Reglas de negocio del Módulo 6 - Gestión de Inventario.

Toda variación del stock pasa por este módulo, de modo que exista un único
lugar donde se actualiza la cantidad, se registra el movimiento y se deja
constancia en el log de auditoría.
"""
from django.db import transaction
from django.db.models import F

from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import MovementType, Stock, StockMovement


def get_quantity(venue, product):
    """Devuelve el stock actual del producto en la sede; cero si no existe."""
    stock = Stock.objects.filter(venue=venue, product=product).first()
    return stock.quantity if stock else 0


@transaction.atomic
def register_entry(*, venue, product, quantity, performed_by, request=None):
    """
    Registra una entrada de mercancía y suma la cantidad al stock de la sede.

    La cantidad debe ser un entero positivo mayor que cero; la validación del
    dato de entrada se hace en el serializador.
    """
    stock, created = Stock.objects.get_or_create(venue=venue, product=product)

    # Se actualiza con F() para evitar perder incrementos simultáneos de dos
    # usuarios registrando entradas del mismo producto a la vez.
    Stock.objects.filter(pk=stock.pk).update(quantity=F("quantity") + quantity)
    stock.refresh_from_db()

    movement = StockMovement.objects.create(
        venue=venue,
        product=product,
        movement_type=MovementType.ENTRY,
        quantity=quantity,
        performed_by=performed_by,
    )

    record_event(
        event_type=EventType.STOCK_ENTRY,
        username=performed_by.username,
        user=performed_by,
        entity="Stock",
        entity_id=stock.id,
        description=(
            f"Entrada de {quantity} unidades de '{product.name}' en la sede "
            f"'{venue.name}'. Stock resultante: {stock.quantity}."
        ),
        request=request,
    )

    return stock, movement
