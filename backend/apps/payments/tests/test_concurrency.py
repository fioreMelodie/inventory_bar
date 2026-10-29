from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.payments.models import Invoice, InvoiceCounter, Payment
from apps.tables.models import Table, TableStatus


class ConcurrentCashPaymentTests(TransactionTestCase):
    def setUp(self):
        venue = Venue.objects.create(name="Central")
        self.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=venue)
        table = Table.objects.create(venue=venue, identifier="Table 1", status=TableStatus.OCCUPIED)
        product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)
        self.order = Order.objects.create(venue=venue, table=table, waiter=self.cashier, status=OrderStatus.IN_CASHIER, total=6000)
        OrderItem.objects.create(order=self.order, product=product, quantity=2, unit_price=3000)

    def submit_parallel(self, keys, methods=None):
        barrier = Barrier(2)
        methods = methods or ["CASH", "CASH"]

        def submit(key, method):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(User.objects.get(pk=self.cashier.pk))
                barrier.wait(timeout=15)
                payload = {"order": self.order.pk, "expected_total": 6000, "idempotency_key": str(key)}
                if method == "CASH":
                    payload["received_amount"] = 10000
                else:
                    payload.update(method=method, terminal_approved=True, approval_reference="AP-123456")
                response = client.post(reverse("payments:cash" if method == "CASH" else "payments:card"), payload, format="json")
                return response.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit, key, method) for key, method in zip(keys, methods)]
            statuses = sorted(future.result(timeout=30) for future in futures)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(InvoiceCounter.objects.get().next_number, 2)
        self.assertEqual(Order.objects.get(pk=self.order.pk).status, OrderStatus.PAID)
        self.assertEqual(Table.objects.get(pk=self.order.table_id).status, TableStatus.FREE)
        return statuses

    @skipUnlessDBFeature("has_select_for_update")
    def test_parallel_same_reference_returns_one_payment(self):
        key = uuid4()
        self.assertEqual(self.submit_parallel([key, key]), [200, 201])

    @skipUnlessDBFeature("has_select_for_update")
    def test_parallel_different_references_cannot_double_charge(self):
        self.assertEqual(self.submit_parallel([uuid4(), uuid4()]), [201, 409])

    @skipUnlessDBFeature("has_select_for_update")
    def test_card_and_cash_cannot_both_be_recorded(self):
        self.assertEqual(self.submit_parallel([uuid4(), uuid4()], ["CASH", "CREDIT_CARD"]), [201, 409])

    @skipUnlessDBFeature("has_select_for_update")
    def test_card_replay_is_idempotent_under_concurrency(self):
        key = uuid4()
        self.assertEqual(self.submit_parallel([key, key], ["DEBIT_CARD", "DEBIT_CARD"]), [200, 201])

    @skipUnlessDBFeature("has_select_for_update")
    def test_credit_and_debit_cannot_both_be_recorded(self):
        self.assertEqual(self.submit_parallel([uuid4(), uuid4()], ["CREDIT_CARD", "DEBIT_CARD"]), [201, 409])
