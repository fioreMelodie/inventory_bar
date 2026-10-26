from unittest.mock import patch
from uuid import uuid4

from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus
from apps.payments.models import Invoice, InvoiceCounter, Payment


class CashPaymentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.venue = Venue.objects.create(name="Central", address="Main street")
        cls.other_venue = Venue.objects.create(name="North")
        cls.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.venue)
        cls.admin = User.objects.create_user(username="admin", full_name="Administrator", role=Role.ADMIN)
        cls.waiter = User.objects.create_user(username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.venue)
        cls.other_cashier = User.objects.create_user(username="other", full_name="Other cashier", role=Role.CASHIER, venue=cls.other_venue)
        cls.product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)

    def setUp(self):
        self.order = self.make_order(self.venue)
        Stock.objects.create(venue=self.venue, product=self.product, quantity=8)
        self.client.force_authenticate(self.cashier)
        self.url = reverse("payments:cash")
        self.payload = {"order": self.order.pk, "received_amount": 10000, "expected_total": 6000, "idempotency_key": str(uuid4())}

    def make_order(self, venue):
        table = Table.objects.create(venue=venue, identifier=f"Table {Table.objects.count() + 1}", status=TableStatus.OCCUPIED)
        order = Order.objects.create(venue=venue, table=table, waiter=self.waiter, status=OrderStatus.IN_CASHIER, total=6000, sent_to_cashier_at=timezone.now())
        OrderItem.objects.create(order=order, product=self.product, quantity=2, unit_price=3000)
        return order

    def pay(self, **changes):
        return self.client.post(self.url, {**self.payload, **changes}, format="json")

    def assert_unpaid(self):
        self.order.refresh_from_db()
        self.order.table.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_CASHIER)
        self.assertEqual(self.order.table.status, TableStatus.OCCUPIED)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(Invoice.objects.exists())
        self.assertFalse(InvoiceCounter.objects.exists())

    def test_cash_payment_closes_order_frees_table_and_preserves_stock(self):
        response = self.pay()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["payment"]["amount"], 6000)
        self.assertEqual(response.data["payment"]["received_amount"], 10000)
        self.assertEqual(response.data["payment"]["change"], 4000)
        self.order.refresh_from_db()
        self.order.table.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.order.table.status, TableStatus.FREE)
        self.assertEqual(Stock.objects.get(venue=self.venue, product=self.product).quantity, 8)
        self.assertEqual(self.client.get(reverse("orders:order-pending")).data["count"], 0)
        self.assertTrue(AuditEvent.objects.filter(event_type=EventType.PAYMENT_PROCESSED).exists())
        self.assertTrue(AuditEvent.objects.filter(event_type=EventType.INVOICE_GENERATED).exists())

    def test_exact_amount_has_zero_change(self):
        response = self.pay(received_amount=6000)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment"]["change"], 0)

    def test_insufficient_amount_saves_nothing(self):
        response = self.pay(received_amount=5999)
        self.assertEqual(response.status_code, 400)
        self.assertIn("received_amount", response.data)
        self.assert_unpaid()

    def test_invalid_amounts_are_rejected(self):
        for amount in (0, -1, 1.5, "invalid", True, 2147483648):
            with self.subTest(amount=amount):
                self.assertEqual(self.pay(received_amount=amount).status_code, 400)
                self.assert_unpaid()

    def test_missing_or_invalid_reference_is_rejected(self):
        for key in (None, "", "invalid"):
            self.assertEqual(self.pay(idempotency_key=key).status_code, 400)
        self.assert_unpaid()

    def test_not_authenticated(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.pay().status_code, 401)
        self.assert_unpaid()

    def test_waiter_cannot_collect(self):
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.pay().status_code, 403)
        self.assert_unpaid()

    def test_other_venue_cannot_collect(self):
        self.client.force_authenticate(self.other_cashier)
        self.assertEqual(self.pay().status_code, 404)
        self.assert_unpaid()

    def test_admin_can_collect_any_venue(self):
        self.client.force_authenticate(self.admin)
        other = self.make_order(self.other_venue)
        self.assertEqual(self.pay(order=other.pk).status_code, 201)
        self.assertEqual(Payment.objects.get().venue_id, self.other_venue.pk)
        self.assertTrue(AuditEvent.objects.filter(event_type=EventType.PAYMENT_PROCESSED, venue=self.other_venue).exists())
        self.assertTrue(AuditEvent.objects.filter(event_type=EventType.INVOICE_GENERATED, venue=self.other_venue).exists())

    def test_open_or_cancelled_order_cannot_be_paid(self):
        for order_status in (OrderStatus.OPEN, OrderStatus.CANCELLED):
            Order.objects.filter(pk=self.order.pk).update(status=order_status)
            self.assertEqual(self.pay().status_code, 409)
            self.assertFalse(Payment.objects.exists())

    def test_same_request_is_idempotent(self):
        first = self.pay()
        second = self.pay()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(InvoiceCounter.objects.get().next_number, 2)
        self.assertEqual(AuditEvent.objects.filter(event_type=EventType.PAYMENT_PROCESSED).count(), 1)

    def test_second_payment_reference_cannot_charge_again(self):
        self.pay()
        self.assertEqual(self.pay(idempotency_key=str(uuid4())).status_code, 409)
        self.assertEqual(Payment.objects.count(), 1)

    def test_reused_key_with_different_amount_is_rejected(self):
        self.pay()
        self.assertEqual(self.pay(received_amount=12000).status_code, 409)
        self.assertEqual(Payment.objects.get().received_amount, 10000)

    def test_key_cannot_be_reused_for_different_order(self):
        self.pay()
        other = self.make_order(self.venue)
        self.assertEqual(self.pay(order=other.pk).status_code, 409)
        other.refresh_from_db()
        self.assertEqual(other.status, OrderStatus.IN_CASHIER)

    def test_retry_does_not_free_table_reopened_after_payment(self):
        self.pay()
        self.client.force_authenticate(self.waiter)
        reopened = self.client.post(reverse("orders:order-list"), {"table": self.order.table_id}, format="json")
        self.assertEqual(reopened.status_code, 201)
        self.client.force_authenticate(self.cashier)
        self.assertEqual(self.pay().status_code, 200)
        self.assertEqual(Table.objects.get(pk=self.order.table_id).status, TableStatus.OCCUPIED)

    def test_paid_order_is_immutable_through_api_and_admin(self):
        self.pay()
        self.client.force_authenticate(self.admin)
        for action in ("order-add-item", "order-cancel", "order-send-to-cashier"):
            response = self.client.post(reverse("orders:" + action, args=[self.order.pk]), {"product": self.product.pk, "quantity": 1}, format="json")
            self.assertEqual(response.status_code, 400)
        self.order.refresh_from_db()
        request = RequestFactory().get("/")
        request.user = self.admin
        self.assertFalse(admin.site._registry[Order].has_change_permission(request, self.order))

    def test_invoice_snapshot_survives_names_and_prices_changes(self):
        self.pay()
        self.product.name = "Renamed coffee"
        self.product.sale_price = 5000
        self.product.save()
        self.venue.name = "Renamed venue"
        self.venue.save()
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.snapshot["venue_name"], "Central")
        self.assertEqual(invoice.snapshot["items"][0]["product_name"], "Coffee")
        self.assertEqual(invoice.snapshot["items"][0]["unit_price"], 3000)
        self.assertEqual(invoice.snapshot["total"], 6000)

    def test_invoice_sequence_is_per_venue(self):
        self.pay()
        second = self.make_order(self.venue)
        self.pay(order=second.pk, idempotency_key=str(uuid4()))
        self.client.force_authenticate(self.admin)
        other = self.make_order(self.other_venue)
        self.pay(order=other.pk, idempotency_key=str(uuid4()))
        self.assertEqual(list(Invoice.objects.filter(venue=self.venue).order_by("sequence").values_list("sequence", flat=True)), [1, 2])
        self.assertEqual(Invoice.objects.get(venue=self.other_venue).sequence, 1)
        self.assertEqual(len(set(Invoice.objects.values_list("number", flat=True))), 3)

    def test_invoice_error_rolls_back_payment_state_and_sequence(self):
        with patch("apps.payments.services.Invoice.objects.create", side_effect=RuntimeError("Invoice failure")):
            with self.assertRaises(RuntimeError):
                self.pay()
        self.assert_unpaid()
        self.assertFalse(AuditEvent.objects.filter(event_type=EventType.PAYMENT_PROCESSED).exists())

    def test_audit_failure_rolls_back_the_whole_transaction(self):
        with patch("apps.payments.services.record_event", side_effect=RuntimeError("Audit failure")):
            with self.assertRaises(RuntimeError):
                self.pay()
        self.assert_unpaid()

    def test_inconsistent_total_cannot_be_collected(self):
        Order.objects.filter(pk=self.order.pk).update(total=1)
        self.assertEqual(self.pay().status_code, 409)
        self.assertFalse(Payment.objects.exists())

    def test_changed_expected_total_is_rejected(self):
        self.assertEqual(self.pay(expected_total=5000).status_code, 409)
        self.assert_unpaid()

    def test_client_cannot_override_total_method_or_change(self):
        response = self.pay(total=1, change=999999, method="CARD", venue=self.other_venue.pk)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment"]["amount"], 6000)
        self.assertEqual(response.data["payment"]["change"], 4000)
        self.assertEqual(response.data["payment"]["method"], "CASH")
        self.assertEqual(response.data["payment"]["venue"], self.venue.pk)

    def test_receipt_permissions_and_paid_order_link(self):
        invoice_id = self.pay().data["invoice"]["id"]
        url = reverse("payments:invoice-detail", args=[invoice_id])
        self.assertEqual(self.client.get(url).status_code, 200)
        detail = self.client.get(reverse("orders:order-detail", args=[self.order.pk])).data
        self.assertEqual(detail["receipt"]["id"], invoice_id)
        self.client.force_authenticate(self.other_cashier)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertIsNone(self.client.get(reverse("orders:order-detail", args=[self.order.pk])).data["receipt"])
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        for method in ("post", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(url, {}, format="json").status_code, 405)

    def test_payment_and_invoice_records_cannot_be_changed_or_deleted(self):
        self.pay()
        for model in (Payment, Invoice):
            obj = model.objects.get()
            with self.assertRaises(NotImplementedError):
                obj.save()
            with self.assertRaises(NotImplementedError):
                obj.delete()
            with self.assertRaises(NotImplementedError):
                model.objects.filter(pk=obj.pk).delete()
            with self.assertRaises(NotImplementedError):
                model.objects.filter(pk=obj.pk).update(pk=obj.pk)

    def test_empty_order_cannot_be_collected(self):
        self.order.items.all().delete()
        self.assertEqual(self.pay().status_code, 409)
        self.assert_unpaid()
