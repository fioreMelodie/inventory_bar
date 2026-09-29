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


class InsufficientStock(Exception):
    """
    No hay unidades suficientes del producto en la sede.

    El mensaje va en inglés porque se muestra directamente al usuario.
    """

    def __init__(self, product, available):
        self.product = product
        self.available = available
        super().__init__(
            f"Not enough stock for {product.name}. Available: {available}."
        )


@transaction.atomic
def discount_for_order(*, order, product, quantity, performed_by, request=None):
    """
    Descuenta del inventario de la sede las unidades agregadas a un pedido.

    El descuento ocurre al agregar el ítem al pedido, no al procesar el pago
    (criterio de la HU16). Si no hay stock suficiente se lanza InsufficientStock
    y no se modifica nada, porque la operación es atómica.
    """
    stock = (
        Stock.objects.select_for_update()
        .filter(venue=order.venue, product=product)
        .first()
    )
    available = stock.quantity if stock else 0

    if available < quantity:
        raise InsufficientStock(product, available)

    Stock.objects.filter(pk=stock.pk).update(quantity=F("quantity") - quantity)
    stock.refresh_from_db()

    StockMovement.objects.create(
        venue=order.venue,
        product=product,
        movement_type=MovementType.ORDER_DISCOUNT,
        quantity=-quantity,
        order=order,
        performed_by=performed_by,
    )

    record_event(
        event_type=EventType.STOCK_DISCOUNT,
        username=performed_by.username,
        user=performed_by,
        entity="Stock",
        entity_id=stock.id,
        description=(
            f"Descuento de {quantity} unidades de '{product.name}' por el pedido "
            f"{order.id} en la sede '{order.venue.name}'. "
            f"Stock resultante: {stock.quantity}."
        ),
        request=request,
    )

    return stock


@transaction.atomic
def restore_for_order(*, order, performed_by, request=None):
    """
    Reintegra al inventario las unidades de un pedido cancelado.

    Solo aplica a pedidos en estado ABIERTO: una vez enviado a caja el pedido
    es inmutable.
    """
    restored = []

    for item in order.items.select_related("product"):
        stock, _ = Stock.objects.get_or_create(venue=order.venue, product=item.product)
        Stock.objects.filter(pk=stock.pk).update(quantity=F("quantity") + item.quantity)
        stock.refresh_from_db()

        StockMovement.objects.create(
            venue=order.venue,
            product=item.product,
            movement_type=MovementType.ORDER_RESTORE,
            quantity=item.quantity,
            order=order,
            performed_by=performed_by,
        )

        record_event(
            event_type=EventType.STOCK_RESTORE,
            username=performed_by.username,
            user=performed_by,
            entity="Stock",
            entity_id=stock.id,
            description=(
                f"Reintegro de {item.quantity} unidades de '{item.product.name}' "
                f"por la cancelación del pedido {order.id} en la sede "
                f"'{order.venue.name}'. Stock resultante: {stock.quantity}."
            ),
            request=request,
        )
        restored.append(stock)

    return restored
