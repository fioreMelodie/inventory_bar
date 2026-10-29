"""Serializadores del Módulo 9 - Pagos y Facturación."""
from rest_framework import serializers

from apps.orders.serializers import OrderItemSerializer

from .models import Invoice, PaymentMethod


class PaymentSerializer(serializers.Serializer):
    """
    Datos del cobro de un pedido (HU23).

    El monto recibido solo aplica al pago en efectivo.
    """

    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        error_messages={
            "invalid_choice": "Select a valid payment method.",
            "required": "Select the payment method.",
        },
    )
    amount_received = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        error_messages={
            "invalid": "The amount received must be a whole number.",
            "min_value": "The amount received cannot be negative.",
        },
    )
    # El cobro con tarjeta ocurre fuera del sistema: el Cajero confirma que el
    # datáfono aprobó la transacción (criterio de la HU24).
    card_approved = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        method = attrs.get("payment_method")

        if method in PaymentMethod.card_methods() and not attrs.get("card_approved"):
            raise serializers.ValidationError(
                {
                    "card_approved": (
                        "Confirm that the card payment was approved on the card reader."
                    )
                }
            )

        # El pedido se cobra con un único método: el campo no admite dos
        # valores, de modo que efectivo y tarjeta no pueden combinarse.
        if method == PaymentMethod.CASH and attrs.get("amount_received") is None:
            raise serializers.ValidationError(
                {"amount_received": "Enter the amount received from the customer."}
            )

        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Factura con la información completa de la transacción.

    Incluye los ítems del pedido con sus cantidades y precios, de modo que la
    factura se baste a sí misma como soporte documental.
    """

    venue_name = serializers.CharField(source="venue.name", read_only=True)
    table_identifier = serializers.CharField(
        source="order.table.identifier", read_only=True
    )
    waiter_name = serializers.CharField(source="order.waiter.full_name", read_only=True)
    cashier_name = serializers.CharField(source="cashier.full_name", read_only=True)
    payment_method_label = serializers.CharField(
        source="get_payment_method_display", read_only=True
    )
    items = OrderItemSerializer(source="order.items", many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "created_at",
            "venue",
            "venue_name",
            "order",
            "table_identifier",
            "waiter_name",
            "cashier_name",
            "payment_method",
            "payment_method_label",
            "total",
            "amount_received",
            "change_given",
            "items",
        )
        read_only_fields = fields
