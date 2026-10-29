from django.conf import settings
from django.db import models
from django.utils import timezone


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NotImplementedError("Payment records are immutable.")

    def delete(self):
        raise NotImplementedError("Payment records cannot be deleted.")


class ImmutableRecord(models.Model):
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise NotImplementedError("Payment records are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Payment records cannot be deleted.")


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CREDIT_CARD = "CREDIT_CARD", "Credit card"
    DEBIT_CARD = "DEBIT_CARD", "Debit card"


class Payment(ImmutableRecord):
    order = models.OneToOneField("orders.Order", on_delete=models.PROTECT, related_name="payment")
    venue = models.ForeignKey("locations.Venue", on_delete=models.PROTECT)
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    method = models.CharField(max_length=12, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    approval_reference = models.CharField(max_length=40, blank=True, default="")
    terminal_approved = models.BooleanField(default=False)
    amount = models.PositiveBigIntegerField()
    received_amount = models.PositiveBigIntegerField()
    change = models.PositiveBigIntegerField()
    idempotency_key = models.UUIDField(unique=True, editable=False)
    paid_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-paid_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_positive_amount"),
            models.CheckConstraint(condition=models.Q(received_amount__gte=models.F("amount")), name="payment_covers_total"),
            models.CheckConstraint(condition=models.Q(change=models.F("received_amount") - models.F("amount")), name="payment_correct_change"),
            models.CheckConstraint(
                condition=(
                    models.Q(method="CASH", approval_reference="", terminal_approved=False)
                    | (models.Q(method__in=["CREDIT_CARD", "DEBIT_CARD"], terminal_approved=True,
                                received_amount=models.F("amount"), change=0)
                       & ~models.Q(approval_reference=""))
                ),
                name="payment_method_details_consistent",
            ),
        ]


class InvoiceCounter(models.Model):
    venue = models.OneToOneField("locations.Venue", on_delete=models.PROTECT, primary_key=True)
    next_number = models.PositiveBigIntegerField(default=1)


class Invoice(ImmutableRecord):
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="invoice")
    venue = models.ForeignKey("locations.Venue", on_delete=models.PROTECT)
    sequence = models.PositiveBigIntegerField()
    number = models.CharField(max_length=60, unique=True)
    issued_at = models.DateTimeField(default=timezone.now, editable=False)
    snapshot = models.JSONField()

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["issued_at", "id"], name="invoice_issued_id_idx"),
            models.Index(fields=["venue", "issued_at", "id"], name="invoice_venue_issued_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["venue", "sequence"], name="unique_invoice_sequence_per_venue"),
        ]
