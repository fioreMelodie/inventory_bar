from rest_framework import serializers

from .models import Invoice, Payment, PaymentMethod
from .validation import normalize_approval_reference


class PaymentRequestSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    expected_total = serializers.IntegerField(min_value=1, max_value=2147483647)
    idempotency_key = serializers.UUIDField()


class CashPaymentSerializer(PaymentRequestSerializer):
    received_amount = serializers.IntegerField(min_value=1, max_value=2147483647)


class CardPaymentSerializer(PaymentRequestSerializer):
    method = serializers.ChoiceField(choices=[
        PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD,
    ])
    approval_reference = serializers.CharField(max_length=40)
    terminal_approved = serializers.BooleanField()

    def to_internal_value(self, data):
        if hasattr(data, "keys") and set(data.keys()) - set(self.fields):
            raise serializers.ValidationError({
                "detail": "Unexpected payment fields. Do not submit card numbers, security codes or cash amounts."
            })
        return super().to_internal_value(data)

    def validate_approval_reference(self, value):
        return normalize_approval_reference(value)

    def validate_terminal_approved(self, value):
        if value is not True:
            raise serializers.ValidationError("Confirm that the payment was approved on the external terminal.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "order", "venue", "cashier", "method", "approval_reference", "terminal_approved", "amount", "received_amount", "change", "paid_at")
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Cost belongs to authorized reports, not customer-facing receipts.
        data["snapshot"] = {**data["snapshot"], "items": [
            {key: value for key, value in item.items() if key != "purchase_price"}
            for item in data["snapshot"]["items"]
        ]}
        return data

    class Meta:
        model = Invoice
        fields = ("id", "number", "venue", "sequence", "issued_at", "snapshot")
        read_only_fields = fields


class InvoiceListSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source="snapshot.venue_name", read_only=True)
    table_identifier = serializers.CharField(source="snapshot.table_identifier", read_only=True)
    total = serializers.IntegerField(source="snapshot.total", read_only=True)
    method = serializers.CharField(source="snapshot.method", read_only=True)

    class Meta:
        model = Invoice
        fields = ("id", "number", "venue", "issued_at", "venue_name", "table_identifier", "total", "method")
        read_only_fields = fields


class ReportDateFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    end_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class InvoiceFilterSerializer(ReportDateFilterSerializer):
    venue = serializers.IntegerField(min_value=1, max_value=9223372036854775807, required=False)
    number = serializers.CharField(max_length=60, required=False)


class RequiredSalesDateFilterSerializer(ReportDateFilterSerializer):
    start_date = serializers.DateField(input_formats=["%Y-%m-%d"])
    end_date = serializers.DateField(input_formats=["%Y-%m-%d"])


class CashierSalesReportFilterSerializer(RequiredSalesDateFilterSerializer):
    product = serializers.CharField(max_length=150, required=False)

    def to_internal_value(self, data):
        if set(data.keys()) - (set(self.fields) | {"page"}):
            raise serializers.ValidationError({"detail": "Only date and product filters are available for your venue report."})
        return super().to_internal_value(data)


class SalesReportFilterSerializer(RequiredSalesDateFilterSerializer):
    venue = serializers.IntegerField(min_value=1, max_value=9223372036854775807, required=False)
    number = serializers.CharField(max_length=60, required=False)
    product = serializers.CharField(max_length=150, required=False)
    category = serializers.CharField(max_length=80, required=False)
    export = serializers.ChoiceField(choices=["csv", "print"], required=False)
