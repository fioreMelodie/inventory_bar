from django.db import transaction
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from apps.accounts.models import Role
from apps.audit.models import EventType
from apps.audit.services import record_event
from apps.locations.models import Venue
from apps.orders.models import Order, OrderStatus
from apps.tables.models import Table, TableStatus

from .models import Invoice, InvoiceCounter, Payment, PaymentMethod
from .validation import normalize_approval_reference


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "This order cannot be paid. Reload the order and try again."


def pay_cash(*, order_id, received_amount, expected_total, idempotency_key, cashier, request=None):
    return _record_payment(
        order_id=order_id, received_amount=received_amount, expected_total=expected_total,
        idempotency_key=idempotency_key, cashier=cashier, request=request,
        method=PaymentMethod.CASH,
    )


def pay_card(*, order_id, method, approval_reference, terminal_approved, expected_total,
             idempotency_key, cashier, request=None):
    if method not in (PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD):
        raise ValidationError({"method": "Select credit card or debit card."})
    if terminal_approved is not True:
        raise ValidationError({"terminal_approved": "Confirm that the payment was approved on the external terminal."})
    try:
        reference = normalize_approval_reference(approval_reference)
    except ValidationError as error:
        raise ValidationError({"approval_reference": error.detail})
    return _record_payment(
        order_id=order_id, received_amount=expected_total, expected_total=expected_total,
        idempotency_key=idempotency_key, cashier=cashier, request=request,
        method=PaymentMethod(method), approval_reference=reference, terminal_approved=True,
    )


@transaction.atomic
def _record_payment(*, order_id, received_amount, expected_total, idempotency_key, cashier,
                    method, approval_reference="", terminal_approved=False, request=None):
    if cashier.role not in (Role.ADMIN, Role.CASHIER):
        raise PermissionDenied("Only cashiers and administrators can record payments.")
    orders = Order.objects.all()
    if cashier.role != Role.ADMIN:
        orders = orders.filter(venue_id=cashier.venue_id)
    reference = orders.filter(pk=order_id).only("table_id").first()
    if reference is None:
        raise NotFound("Order not found.")

    # La mesa se bloquea primero, igual que al abrir un pedido.
    table = Table.objects.select_for_update().get(pk=reference.table_id)
    order = Order.objects.select_for_update().get(pk=order_id)
    existing = Payment.objects.filter(order=order).first()
    if existing:
        if (existing.idempotency_key == idempotency_key
                and existing.received_amount == received_amount
                and existing.amount == expected_total
                and existing.method == method
                and existing.approval_reference == approval_reference
                and existing.terminal_approved == terminal_approved
                and existing.cashier_id == cashier.pk):
            return existing, False
        raise PaymentConflict("This order has already been paid. Reload it to view the receipt.")
    if Payment.objects.filter(idempotency_key=idempotency_key).exists():
        raise PaymentConflict("This payment reference was already used for another order.")
    if order.status != OrderStatus.IN_CASHIER:
        raise PaymentConflict("Only orders sent to the cashier can be paid.")
    if table.status != TableStatus.OCCUPIED:
        raise PaymentConflict("The table status is inconsistent. Reload the order.")
    if order.venue_id != table.venue_id or Order.objects.filter(
        table=table, status__in=[OrderStatus.OPEN, OrderStatus.IN_CASHIER],
    ).exclude(pk=order.pk).exists():
        raise PaymentConflict("The table has inconsistent active orders and must be reviewed.")
    items = list(order.items.select_related("product").all())
    total = sum(item.quantity * item.unit_price for item in items)
    if not items or total <= 0 or total != order.total:
        raise PaymentConflict("The order total is inconsistent and must be reviewed before payment.")
    if expected_total != total:
        raise PaymentConflict("The order total changed. Reload the order before confirming payment.")
    if received_amount < total:
        raise ValidationError({"received_amount": "Received amount must cover the order total."})

    venue = Venue.objects.select_for_update().get(pk=order.venue_id)
    counter, _ = InvoiceCounter.objects.get_or_create(venue=venue)
    sequence = counter.next_number
    counter.next_number += 1
    counter.save(update_fields=["next_number"])
    payment = Payment.objects.create(
        order=order, venue=venue, cashier=cashier, amount=total,
        received_amount=received_amount, change=received_amount - total,
        idempotency_key=idempotency_key,
        method=method, approval_reference=approval_reference, terminal_approved=terminal_approved,
    )
    invoice = Invoice.objects.create(
        payment=payment, venue=venue, sequence=sequence,
        number=f"V{venue.pk:03d}-{sequence:06d}", issued_at=payment.paid_at,
        snapshot={
            "order_id": order.pk, "venue_name": venue.name, "venue_address": venue.address,
            "table_identifier": table.identifier, "waiter_name": order.waiter.full_name,
            "cashier_name": cashier.full_name, "method": method, "currency": "COP",
            "approval_reference": approval_reference, "terminal_approved": terminal_approved,
            "items": [
                {"product_id": item.product_id, "product_name": item.product.name,
                 "purchase_price": item.product.purchase_price, "category": item.product.category,
                 "quantity": item.quantity, "unit_price": item.unit_price,
                 "subtotal": item.quantity * item.unit_price}
                for item in items
            ],
            "total": total, "received_amount": received_amount, "change": payment.change,
        },
    )
    order.status = OrderStatus.PAID
    order.save(update_fields=["status"])
    table.status = TableStatus.FREE
    table.save(update_fields=["status", "updated_at"])
    record_event(
        event_type=EventType.PAYMENT_PROCESSED, username=cashier.username, user=cashier,
        entity="Payment", entity_id=payment.pk, venue=venue,
        description=(
            f"{method.label} payment for order {order.pk} at venue '{venue.name}': {total} COP. "
            + (f"Terminal approval reference: {approval_reference}."
               if terminal_approved else f"Received: {received_amount}; change: {payment.change}.")
        ),
        request=request,
    )
    record_event(
        event_type=EventType.INVOICE_GENERATED, username=cashier.username, user=cashier,
        entity="Invoice", entity_id=invoice.pk, venue=venue,
        description=f"Generated receipt {invoice.number} for order {order.pk} at venue '{venue.name}'.",
        request=request,
    )
    return payment, True
