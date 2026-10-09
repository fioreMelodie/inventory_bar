"""
Reglas de negocio del Módulo 9 - Pagos y Facturación.

Concentra el registro del pago: genera la factura, cierra el pedido y libera
la mesa en una sola transacción, de modo que no pueda quedar un pedido cobrado
sin factura ni una mesa ocupada sin pedido activo.
"""
from django.db import transaction
from django.db.models import Max

from apps.audit.models import EventType
from apps.audit.services import record_event
from apps.locations.models import Venue
from apps.orders.models import OrderStatus
from apps.tables.models import TableStatus

from .models import Invoice


class PaymentError(Exception):
    """El pago no puede registrarse. El mensaje se muestra al usuario."""


def build_invoice_number(venue, sequence):
    """
    Construye el número visible de la factura.

    Incluye el identificador de la sede para que el consecutivo sea claramente
    independiente entre sedes.
    """
    return f"F-{venue.id:02d}-{sequence:06d}"


@transaction.atomic
def register_payment(*, order, cashier, payment_method, amount_received=None, request=None):
    """
    Registra el pago de un pedido y genera su factura.

    El pedido debe estar en caja. Al completarse, queda en estado PAGADO, la
    mesa vuelve a LIBRE y la factura queda disponible para consulta.
    """
    if order.status != OrderStatus.IN_CASHIER:
        raise PaymentError("Only orders sent to the cashier can be charged.")

    if Invoice.objects.filter(order=order).exists():
        raise PaymentError("This order has already been charged.")

    change = 0
    if payment_method == "CASH":
        if amount_received is None:
            raise PaymentError("Enter the amount received from the customer.")
        if amount_received < order.total:
            raise PaymentError(
                "The amount received is lower than the order total."
            )
        change = amount_received - order.total
    else:
        # En los pagos con tarjeta el cobro se hace en el datáfono externo, de
        # modo que no hay monto recibido ni cambio que calcular.
        amount_received = None

    # Se bloquea la sede para que dos cajeros cobrando a la vez no obtengan el
    # mismo consecutivo.
    venue = Venue.objects.select_for_update().get(pk=order.venue_id)
    last_sequence = (
        Invoice.objects.filter(venue=venue).aggregate(Max("sequence"))["sequence__max"]
        or 0
    )
    sequence = last_sequence + 1

    invoice = Invoice.objects.create(
        number=build_invoice_number(venue, sequence),
        sequence=sequence,
        venue=venue,
        order=order,
        cashier=cashier,
        payment_method=payment_method,
        total=order.total,
        amount_received=amount_received,
        change_given=change,
    )

    order.status = OrderStatus.PAID
    order.paid_at = invoice.created_at
    order.save(update_fields=["status", "paid_at"])

    table = order.table
    table.status = TableStatus.FREE
    table.save(update_fields=["status", "updated_at"])

    record_event(
        event_type=EventType.PAYMENT_REGISTERED,
        username=cashier.username,
        user=cashier,
        entity="Invoice",
        entity_id=invoice.id,
        description=(
            f"Pago del pedido {order.id} por {order.total} mediante "
            f"{invoice.get_payment_method_display()}. "
            f"Factura {invoice.number} generada en la sede '{venue.name}'. "
            f"Mesa '{table.identifier}' liberada."
        ),
        request=request,
    )

    return invoice
