from unittest.mock import patch
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.payments.models import Invoice, InvoiceCounter, Payment, PaymentMethod
from apps.tables.models import Table, TableStatus


class CardPaymentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.venue = Venue.objects.create(name="Central")
        cls.other_venue = Venue.objects.create(name="North")
        cls.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.venue)
        cls.admin = User.objects.create_user(username="admin", full_name="Administrator", role=Role.ADMIN)
        cls.waiter = User.objects.create_user(username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.venue)
        cls.other = User.objects.create_user(username="other", full_name="Other cashier", role=Role.CASHIER, venue=cls.other_venue)
        cls.product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)

    def setUp(self):
        self.order = self.make_order(self.venue)
        Stock.objects.create(venue=self.venue, product=self.product, quantity=8)
        self.client.force_authenticate(self.cashier)
        self.url = reverse("payments:card")
        self.payload = {
            "order": self.order.pk, "method": "CREDIT_CARD", "approval_reference": "APP-123456",
            "terminal_approved": True, "expected_total": 6000, "idempotency_key": str(uuid4()),
        }

    def make_order(self, venue):
        table = Table.objects.create(venue=venue, identifier=f"Table {Table.objects.count() + 1}", status=TableStatus.OCCUPIED)
        order = Order.objects.create(venue=venue, table=table, waiter=self.waiter, status=OrderStatus.IN_CASHIER, total=6000, sent_to_cashier_at=timezone.now())
        OrderItem.objects.create(order=order, product=self.product, quantity=2, unit_price=3000)
        return order

    def pay(self, **changes):
        return self.client.post(self.url, {**self.payload, **changes}, format="json")

    def assert_unpaid(self):
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_CASHIER)
        self.assertEqual(Table.objects.get(pk=self.order.table_id).status, TableStatus.OCCUPIED)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceCounter.objects.exists())

    def test_credit_and_debit_pay_full_total_without_change(self):
        for method in (PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD):
            order = self.order if method == PaymentMethod.CREDIT_CARD else self.make_order(self.venue)
            response = self.pay(order=order.pk, method=method, idempotency_key=str(uuid4()))
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(response.data["payment"]["method"], method)
            self.assertEqual(response.data["payment"]["amount"], 6000)
            self.assertEqual(response.data["payment"]["received_amount"], 6000)
            self.assertEqual(response.data["payment"]["change"], 0)
            self.assertTrue(response.data["payment"]["terminal_approved"])
            order.refresh_from_db()
            self.assertEqual(order.status, OrderStatus.PAID)
            self.assertEqual(Table.objects.get(pk=order.table_id).status, TableStatus.FREE)
        self.assertEqual(Stock.objects.get(venue=self.venue, product=self.product).quantity, 8)
        self.assertEqual(self.client.get(reverse("orders:order-pending")).data["count"], 0)

    def test_terminal_confirmation_is_required(self):
        for approved in (False, None, "not approved"):
            self.assertEqual(self.pay(terminal_approved=approved).status_code, 400)
        payload = {key: value for key, value in self.payload.items() if key != "terminal_approved"}
        self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 400)
        self.assert_unpaid()

    def test_only_credit_and_debit_are_card_methods(self):
        for method in ("CASH", "CARD", "CASH,CREDIT_CARD", "", None):
            self.assertEqual(self.pay(method=method).status_code, 400)
        self.assert_unpaid()

    def test_reference_is_required_and_has_restricted_format(self):
        for reference in ("", "  ", "AB", "A" * 41, "APP 123", "<invalid>", None):
            with self.subTest(reference=reference):
                response = self.pay(approval_reference=reference)
                self.assertEqual(response.status_code, 400)
                self.assertIn("approval_reference", response.data)
        self.assert_unpaid()

    def test_card_number_like_references_are_not_saved(self):
        for reference in ("1234567890123", "1234-5678-9012-3456", "APP-1234-5678-9012-3456"):
            response = self.pay(approval_reference=reference)
            self.assertEqual(response.status_code, 400)
            self.assertIn("Do not enter a card number", str(response.data))
        self.assert_unpaid()
        self.assertFalse(AuditEvent.objects.exists())

    def test_cash_or_sensitive_extra_fields_are_rejected(self):
        for field in ("received_amount", "cash_amount", "change", "card_number", "cvv", "cardholder", "expiry"):
            with self.subTest(field=field):
                self.assertEqual(self.pay(**{field: "not-to-store"}).status_code, 400)
        self.assert_unpaid()

    def test_reference_normalization_is_idempotent(self):
        first = self.pay(approval_reference=" app-123456 ")
        second = self.pay(approval_reference="APP-123456")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertEqual(Payment.objects.get().approval_reference, "APP-123456")
        self.assertEqual(InvoiceCounter.objects.get().next_number, 2)
        self.assertEqual(AuditEvent.objects.filter(event_type=EventType.PAYMENT_PROCESSED).count(), 1)

    def test_replay_cannot_change_card_type_or_reference(self):
        self.pay()
        self.assertEqual(self.pay(method="DEBIT_CARD").status_code, 409)
        self.assertEqual(self.pay(approval_reference="OTHER-123").status_code, 409)
        self.assertEqual(Payment.objects.count(), 1)

    def test_cash_cannot_follow_a_card_payment(self):
        self.pay()
        response = self.client.post(
            reverse("payments:cash"), {"order": self.order.pk, "received_amount": 10000,
            "expected_total": 6000, "idempotency_key": str(uuid4())}, format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Payment.objects.get().method, "CREDIT_CARD")

    def test_card_cannot_follow_a_cash_payment_even_with_same_key(self):
        response = self.client.post(
            reverse("payments:cash"), {"order": self.order.pk, "received_amount": 6000,
            "expected_total": 6000, "idempotency_key": self.payload["idempotency_key"]}, format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.pay().status_code, 409)
        self.assertEqual(Payment.objects.get().method, "CASH")

    def test_unauthenticated_or_waiter_cannot_record_card_payment(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.pay().status_code, 401)
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.pay().status_code, 403)
        self.assert_unpaid()

    def test_cashier_cannot_pay_other_venue(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.pay().status_code, 404)
        self.assert_unpaid()

    def test_admin_can_pay_other_venue(self):
        self.client.force_authenticate(self.admin)
        order = self.make_order(self.other_venue)
        self.assertEqual(self.pay(order=order.pk, method="DEBIT_CARD").status_code, 201)
        self.assertEqual(Payment.objects.get().venue_id, self.other_venue.pk)

    def test_only_pending_orders_can_be_paid(self):
        for order_status in (OrderStatus.OPEN, OrderStatus.CANCELLED):
            Order.objects.filter(pk=self.order.pk).update(status=order_status)
            self.assertEqual(self.pay().status_code, 409)
            self.assertFalse(Payment.objects.exists())

    def test_card_type_and_reference_are_frozen_in_receipt_and_audit(self):
        response = self.pay(method="DEBIT_CARD")
        self.assertEqual(response.status_code, 201)
        snapshot = response.data["invoice"]["snapshot"]
        self.assertEqual(snapshot["method"], "DEBIT_CARD")
        self.assertEqual(snapshot["approval_reference"], "APP-123456")
        self.assertTrue(snapshot["terminal_approved"])
        event = AuditEvent.objects.get(event_type=EventType.PAYMENT_PROCESSED)
        self.assertIn("Debit card payment", event.description)
        self.assertIn("APP-123456", event.description)
        self.assertTrue(AuditEvent.objects.filter(event_type=EventType.INVOICE_GENERATED).exists())
        self.product.name = "Renamed coffee"
        self.product.save()
        self.assertEqual(Invoice.objects.get().snapshot["items"][0]["product_name"], "Coffee")

    def test_changed_expected_total_cannot_be_confirmed(self):
        self.assertEqual(self.pay(expected_total=5000).status_code, 409)
        self.assert_unpaid()

    def test_invoice_failure_rolls_back_card_payment(self):
        with patch("apps.payments.services.Invoice.objects.create", side_effect=RuntimeError("Invoice failure")):
            with self.assertRaises(RuntimeError):
                self.pay()
        self.assert_unpaid()

    def test_audit_failure_rolls_back_card_payment(self):
        with patch("apps.payments.services.record_event", side_effect=RuntimeError("Audit failure")):
            with self.assertRaises(RuntimeError):
                self.pay()
        self.assert_unpaid()

    def test_database_enforces_method_metadata_consistency(self):
        base = {
            "order": self.order, "venue": self.venue, "cashier": self.cashier, "amount": 6000,
            "received_amount": 6000, "change": 0, "idempotency_key": uuid4(),
        }
        for metadata in (
            {"method": "CREDIT_CARD", "terminal_approved": False, "approval_reference": "AP-123"},
            {"method": "DEBIT_CARD", "terminal_approved": True, "approval_reference": ""},
            {"method": "CASH", "terminal_approved": True, "approval_reference": "AP-123"},
            {"method": "CREDIT_CARD", "terminal_approved": True, "approval_reference": "AP-123", "received_amount": 10000, "change": 4000},
        ):
            with self.subTest(metadata=metadata):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Payment.objects.create(**{**base, **metadata})
        self.assert_unpaid()
