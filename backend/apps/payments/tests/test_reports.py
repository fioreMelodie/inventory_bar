import csv
import io
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4
from time import perf_counter

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus
from apps.payments.models import Invoice, Payment
from apps.payments.services import pay_cash


class SalesReportFixture:
    def report(self, params=None):
        return self.client.get(self.url, {"start_date": "1900-01-01", "end_date": "9998-12-31", **(params or {})})

    @classmethod
    def setUpTestData(cls):
        cls.venue = Venue.objects.create(name="Central")
        cls.north = Venue.objects.create(name="North", is_active=False)
        cls.admin = User.objects.create_user(username="admin", full_name="Administrator", role=Role.ADMIN)
        cls.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.venue)
        cls.waiter = User.objects.create_user(username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.venue)
        cls.product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)
        cls.tea = Product.objects.create(name="Tea", product_type="Beverage", category="Tea", purchase_price=500, sale_price=2000)
        cls.url = reverse("payments:sales-report")

    def issue(self, venue=None, product=None, timestamp="2026-10-25T17:00:00", legacy=False):
        venue, product = venue or self.venue, product or self.product
        table = Table.objects.create(venue=venue, identifier=str(Table.objects.count() + 1), status=TableStatus.OCCUPIED)
        order = Order.objects.create(venue=venue, table=table, waiter=self.waiter, status=OrderStatus.IN_CASHIER, total=2 * product.sale_price)
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=product.sale_price)
        create_payment, create_invoice = Payment.objects.create, Invoice.objects.create

        def snapshot(**kwargs):
            if legacy:
                for item in kwargs["snapshot"]["items"]:
                    item.pop("purchase_price", None)
                    item.pop("category", None)
            return create_invoice(**kwargs)

        with patch("apps.payments.services.Payment.objects.create", side_effect=lambda **kwargs: create_payment(**kwargs, paid_at=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc))), patch("apps.payments.services.Invoice.objects.create", side_effect=snapshot):
            payment, _ = pay_cash(order_id=order.pk, expected_total=order.total, received_amount=order.total, idempotency_key=uuid4(), cashier=self.admin)
        return payment.invoice


class SalesReportTests(SalesReportFixture, APITestCase):
    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_paid_sales_totals_are_consolidated_across_venues(self):
        self.issue()
        self.issue(self.north, self.tea)
        data = self.report().data
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["summary"], {"sales": 10000, "purchase_value": 3000, "profit": 7000, "quantity": 4, "transactions": 2, "missing_cost_lines": 0, "currency": "COP"})
        self.assertEqual(set(data["categories"]), {"Coffee", "Tea"})

    def test_non_paid_orders_are_excluded(self):
        for state in (OrderStatus.OPEN, OrderStatus.IN_CASHIER, OrderStatus.CANCELLED):
            invoice = self.issue()
            Order.objects.filter(pk=invoice.payment.order_id).update(status=state)
        self.assertEqual(self.report().data["count"], 0)

    def test_combined_filters_and_inactive_venue(self):
        invoice = self.issue(self.north, self.tea)
        self.issue()
        filters = {"venue": self.north.pk, "start_date": "2026-10-25", "end_date": "2026-10-25", "product": "tEa", "category": "Tea"}
        rows = self.report(filters).data["results"]
        self.assertEqual([row["invoice_id"] for row in rows], [invoice.pk])
        self.assertEqual(self.report({**filters, "category": "Coffee"}).data["count"], 0)
        self.assertEqual(self.report({"product": str(self.tea.pk)}).data["count"], 1)

    def test_dates_use_bogota_boundaries(self):
        for timestamp in ("2026-10-25T04:59:59", "2026-10-25T05:00:00", "2026-10-26T04:59:59", "2026-10-26T05:00:00"):
            self.issue(timestamp=timestamp)
        data = self.report({"start_date": "2026-10-25", "end_date": "2026-10-25"}).data
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["summary"]["sales"], 12000)

    def test_no_implicit_history_limit(self):
        self.issue(timestamp="2010-01-01T17:00:00")
        self.assertEqual(self.report().data["count"], 1)

    def test_cost_category_and_names_stay_frozen_after_catalog_changes(self):
        self.issue()
        Product.objects.filter(pk=self.product.pk).update(name="Changed", category="Tea", purchase_price=2500, sale_price=5000)
        Venue.objects.filter(pk=self.venue.pk).update(name="Changed venue")
        row = self.report({"category": "Coffee"}).data["results"][0]
        self.assertEqual((row["product_name"], row["venue_name"], row["purchase_value"], row["sale_value"], row["profit"]), ("Coffee", "Central", 2000, 6000, 4000))

    def test_legacy_costs_are_not_guessed_or_excluded(self):
        old = self.issue(legacy=True)
        self.issue()
        data = self.report().data
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["summary"]["sales"], 12000)
        self.assertIsNone(data["summary"]["profit"])
        self.assertIsNone(data["summary"]["purchase_value"])
        self.assertEqual(data["summary"]["missing_cost_lines"], 1)
        rows = self.report({"category": "__unrecorded__"}).data["results"]
        self.assertEqual([row["invoice_id"] for row in rows], [old.pk])

    def test_receipt_does_not_expose_report_costs(self):
        invoice = self.issue()
        self.assertEqual(invoice.snapshot["items"][0]["purchase_price"], 1000)
        self.client.force_authenticate(self.cashier)
        data = self.client.get(reverse("payments:invoice-detail", args=[invoice.pk])).data
        self.assertNotIn("purchase_price", data["snapshot"]["items"][0])
        invoice.refresh_from_db()
        self.assertEqual(invoice.snapshot["items"][0]["purchase_price"], 1000)

    def test_report_and_exports_are_admin_only(self):
        for user, status in ((self.cashier, 403), (self.waiter, 403), (None, 401)):
            self.client.force_authenticate(user)
            for params in ({}, {"export": "csv"}, {"export": "print"}):
                self.assertEqual(self.report(params).status_code, status)

    def test_invalid_filters_are_rejected(self):
        for params in ({"start_date": "invalid"}, {"start_date": "2026-10-26", "end_date": "2026-10-25"}, {"venue": -1}, {"export": "pdf"}, {"product": "x" * 151}):
            self.assertEqual(self.report(params).status_code, 400)

    def test_summary_covers_all_pages_and_exports_include_all_lines(self):
        for _ in range(26):
            self.issue()
        first = self.report().data
        second = self.report({"page": 2}).data
        self.assertEqual((len(first["results"]), len(second["results"])), (25, 1))
        self.assertEqual(first["summary"]["sales"], 156000)
        self.assertEqual(first["summary"], second["summary"])
        response = self.report({"export": "csv", "page": 2})
        self.assertEqual(response["Cache-Control"], "no-store")
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertEqual(len(rows), 27)
        self.assertIn("-05:00", rows[1][1])
        self.assertEqual(len(self.report({"export": "print", "page": 2}).data["results"]), 26)

    def test_csv_escapes_formula_names_and_marks_unknown_costs(self):
        Product.objects.filter(pk=self.product.pk).update(name="=SUM(1,1)")
        self.product.refresh_from_db()
        self.issue(legacy=True)
        rows = list(csv.reader(io.StringIO(self.report({"export": "csv"}).content.decode())))
        self.assertEqual(rows[1][4], "'=SUM(1,1)")
        self.assertEqual(rows[1][7], "Not recorded")

    def test_empty_report_has_zero_totals_and_is_read_only(self):
        data = self.report().data
        self.assertEqual(data["summary"]["profit"], 0)
        self.assertEqual(data["count"], 0)
        for method in ("post", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url, {}, format="json").status_code, 405)


class CashierSalesReportTests(SalesReportFixture, APITestCase):
    def setUp(self):
        self.client.force_authenticate(self.cashier)
        self.url = reverse("payments:cashier-sales-report")

    def test_own_venue_only_and_explicit_response_allowlist(self):
        self.issue()
        self.issue(self.north, self.tea)
        response = self.report()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["summary"], {"sales": 6000, "quantity": 2, "transactions": 1, "currency": "COP"})
        self.assertEqual(set(response.data["results"][0]), {"id", "issued_at", "product_id", "product_name", "quantity", "sale_value"})
        self.assertNotIn("categories", response.data)

    def test_forged_venue_category_and_exports_are_rejected(self):
        self.issue(self.north)
        for params in ({"venue": self.north.pk}, {"category": "Coffee"}, {"export": "csv"}, {"export": "print"}, {"number": "V001"}, {"profit": "true"}):
            with self.subTest(params=params):
                self.assertEqual(self.report(params).status_code, 400)

    def test_admin_report_remains_forbidden_for_cashier(self):
        for params in ({}, {"export": "csv"}, {"export": "print"}):
            self.assertEqual(self.client.get(reverse("payments:sales-report"), params).status_code, 403)

    def test_other_roles_and_anonymous_cannot_access_cashier_report(self):
        for user, expected in ((self.admin, 403), (self.waiter, 403), (None, 401)):
            self.client.force_authenticate(user)
            self.assertEqual(self.report().status_code, expected)

    def test_cashier_without_assigned_venue_is_denied(self):
        self.issue()
        self.cashier.venue = None
        self.assertEqual(self.report().status_code, 403)

    def test_dates_product_and_venue_scope_combine(self):
        self.issue(product=self.tea, timestamp="2010-01-01T17:00:00")
        self.issue()
        self.issue(self.north, self.tea, timestamp="2010-01-01T17:00:00")
        params = {"start_date": "2010-01-01", "end_date": "2010-01-01", "product": "tEa"}
        data = self.report(params).data
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["summary"]["sales"], 4000)
        self.assertEqual(self.report({**params, "product": str(self.tea.pk)}).data["count"], 1)

    def test_bogota_day_inclusive_limits(self):
        for timestamp in ("2026-10-25T04:59:59", "2026-10-25T05:00:00", "2026-10-26T04:59:59", "2026-10-26T05:00:00"):
            self.issue(timestamp=timestamp)
        self.assertEqual(self.report({"start_date": "2026-10-25", "end_date": "2026-10-25"}).data["count"], 2)

    def test_only_paid_orders_and_unlimited_history(self):
        self.issue(timestamp="2010-01-01T17:00:00", legacy=True)
        for state in (OrderStatus.OPEN, OrderStatus.IN_CASHIER, OrderStatus.CANCELLED):
            invoice = self.issue()
            Order.objects.filter(pk=invoice.payment.order_id).update(status=state)
        self.assertEqual(self.report().data["count"], 1)

    def test_pagination_totals_and_pages_do_not_leak_foreign_sales(self):
        for _ in range(26):
            self.issue()
        self.issue(self.north, self.tea)
        first, second = self.report().data, self.report({"page": 2}).data
        self.assertEqual((first["count"], len(first["results"]), len(second["results"])), (26, 25, 1))
        self.assertEqual(first["summary"], second["summary"])
        self.assertEqual(first["summary"]["sales"], 156000)
        self.assertEqual(self.report({"page": 3}).status_code, 404)

    def test_invalid_dates_read_only_and_empty_state(self):
        self.assertEqual(self.report().data["summary"]["sales"], 0)
        for params in ({"start_date": "invalid"}, {"start_date": "2026-10-26", "end_date": "2026-10-25"}):
            self.assertEqual(self.report(params).status_code, 400)
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url, {}, format="json").status_code, 405)

    def test_stored_product_values_survive_catalog_changes(self):
        self.issue()
        Product.objects.filter(pk=self.product.pk).update(name="Changed", sale_price=5000)
        row = self.report().data["results"][0]
        self.assertEqual((row["product_name"], row["sale_value"]), ("Coffee", 6000))


class CombinedSalesReportTests(SalesReportFixture, APITestCase):
    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_both_dates_are_required_for_reports_and_admin_outputs(self):
        for user, route in ((self.admin, "sales-report"), (self.cashier, "cashier-sales-report")):
            self.client.force_authenticate(user)
            for params in ({}, {"start_date": "2026-10-25"}, {"end_date": "2026-10-25"},
                           {"start_date": "", "end_date": "2026-10-25"}):
                response = self.client.get(reverse("payments:" + route), params)
                self.assertEqual(response.status_code, 400)
            self.assertEqual(self.client.get(reverse("payments:" + route), {"start_date": "2026-10-25", "end_date": "2026-10-25"}).status_code, 200)
        self.client.force_authenticate(self.admin)
        for output in ("csv", "print"):
            self.assertEqual(self.client.get(self.url, {"export": output}).status_code, 400)

    def test_filters_only_reduce_the_matching_set(self):
        self.issue()
        self.issue(self.north)
        target = self.issue(product=self.tea)
        self.issue(product=self.tea, timestamp="2020-01-01T17:00:00")
        filters = {"start_date": "2026-10-25", "end_date": "2026-10-25"}
        previous = {row["invoice_id"] for row in self.report(filters).data["results"]}
        for key, value in (("venue", self.venue.pk), ("product", "Tea"), ("category", "Tea")):
            filters[key] = value
            current = {row["invoice_id"] for row in self.report(filters).data["results"]}
            self.assertTrue(current.issubset(previous))
            previous = current
        self.assertEqual(previous, {target.pk})
        self.assertEqual(self.report({**filters, "category": "Coffee"}).data["count"], 0)

    def test_descending_dates_and_ties_are_stable_for_both_roles(self):
        early = self.issue(timestamp="2026-10-24T17:00:00")
        same = self.issue(timestamp="2026-10-25T17:00:00")
        latest = self.issue(timestamp="2026-10-25T17:00:00")
        expected = [f"{invoice.pk}-0" for invoice in (latest, same, early)]
        for user, route in ((self.admin, "sales-report"), (self.cashier, "cashier-sales-report")):
            self.client.force_authenticate(user)
            data = self.client.get(reverse("payments:" + route), {"start_date": "2026-10-24", "end_date": "2026-10-25"}).data
            self.assertEqual([row["id"] for row in data["results"]], expected)

    def test_receipt_history_dates_remain_optional(self):
        self.issue()
        self.assertEqual(self.client.get(reverse("payments:invoice-list")).status_code, 200)

    def test_combined_report_performance_on_2001_paid_lines(self):
        base = self.issue()
        order = base.payment.order
        count = 2000
        orders = Order.objects.bulk_create([
            Order(venue=self.venue, table=order.table, waiter=self.waiter, status=OrderStatus.PAID, total=6000)
            for _ in range(count)
        ])
        # MySQL does not populate auto IDs on bulk_create; reload fixture rows.
        orders = list(Order.objects.exclude(pk=order.pk).order_by("pk"))
        OrderItem.objects.bulk_create([
            OrderItem(order=item, product=self.product, quantity=2, unit_price=3000) for item in orders
        ])
        payments = Payment.objects.bulk_create([
            Payment(order=item, venue=self.venue, cashier=self.admin, amount=6000, received_amount=6000,
                    change=0, idempotency_key=uuid4(), paid_at=base.issued_at) for item in orders
        ])
        payments = list(Payment.objects.exclude(pk=base.payment_id).order_by("pk"))
        Invoice.objects.bulk_create([
            Invoice(payment=payment, venue=self.venue, sequence=index + 2,
                    number=f"V{self.venue.pk:03d}-{index + 2:06d}", issued_at=base.issued_at,
                    snapshot={**base.snapshot, "order_id": payment.order_id})
            for index, payment in enumerate(payments)
        ])
        timings = []
        for user, route, extras in ((self.admin, "sales-report", {"venue": self.venue.pk, "category": "Coffee"}),
                                    (self.cashier, "cashier-sales-report", {})):
            self.client.force_authenticate(user)
            params = {"start_date": "2026-10-25", "end_date": "2026-10-25", "product": "Coffee", **extras}
            for page in (1, 2):
                started = perf_counter()
                with self.assertNumQueries(1):
                    response = self.client.get(reverse("payments:" + route), {**params, "page": page})
                elapsed = perf_counter() - started
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 2001)
                self.assertEqual(response.data["summary"]["sales"], 12006000)
                self.assertLess(elapsed, 2.0, f"{route}: {elapsed:.3f}s")
                timings.append(f"{route}/page-{page}={elapsed:.3f}s")
        print("HU29 benchmark (2001 paid lines): " + ", ".join(timings))
