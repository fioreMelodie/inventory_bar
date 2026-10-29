from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch
from uuid import uuid4

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus
from apps.payments.models import Invoice, Payment
from apps.payments.services import pay_cash


class InvoicePanelTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.venue = Venue.objects.create(name="Central")
        cls.other_venue = Venue.objects.create(name="North")
        cls.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.venue)
        cls.admin = User.objects.create_user(username="admin", full_name="Administrator", role=Role.ADMIN)
        cls.waiter = User.objects.create_user(username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.venue)
        cls.product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)
        cls.local = cls.issue(cls.venue, 1)
        cls.remote = cls.issue(cls.other_venue, 1)
        cls.url = reverse("payments:invoice-list")

    @classmethod
    def issue(cls, venue, identifier):
        table = Table.objects.create(venue=venue, identifier=str(identifier), status=TableStatus.OCCUPIED)
        order = Order.objects.create(venue=venue, table=table, waiter=cls.waiter, status=OrderStatus.IN_CASHIER, total=3000, sent_to_cashier_at=timezone.now())
        OrderItem.objects.create(order=order, product=cls.product, quantity=1, unit_price=3000)
        payment, _ = pay_cash(order_id=order.pk, received_amount=3000, expected_total=3000, idempotency_key=uuid4(), cashier=cls.admin)
        return payment.invoice

    def setUp(self):
        self.client.force_authenticate(self.cashier)

    def test_cashier_sees_only_own_venue_in_list_and_detail(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.local.pk)
        self.assertEqual(self.client.get(reverse("payments:invoice-detail", args=[self.remote.pk])).status_code, 404)

    def test_filter_cannot_expand_cashier_scope(self):
        response = self.client.get(self.url, {"venue": self.other_venue.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_admin_sees_all_and_can_filter(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url).data["count"], 2)
        response = self.client.get(self.url, {"venue": self.other_venue.pk})
        self.assertEqual([item["id"] for item in response.data["results"]], [self.remote.pk])
        self.assertEqual(self.client.get(reverse("payments:invoice-detail", args=[self.remote.pk])).status_code, 200)

    def test_waiter_and_anonymous_cannot_list(self):
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_invalid_venue_is_a_validation_error(self):
        for value in ("abc", "0", "-1", "1.5", "9223372036854775808"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(self.url, {"venue": value}).status_code, 400)

    def test_nonexistent_venue_is_empty(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(self.url, {"venue": 99999}).data["count"], 0)

    def test_stable_paginated_order(self):
        for identifier in range(2, 27):
            self.issue(self.venue, identifier)
        invoices = list(Invoice.objects.filter(venue=self.venue))
        expected = [invoice.pk for invoice in sorted(invoices, key=lambda i: (i.issued_at, i.pk), reverse=True)]
        first = self.client.get(self.url).data
        second = self.client.get(self.url, {"page": 2}).data
        self.assertEqual(first["count"], 26)
        self.assertEqual(len(first["results"]), 25)
        self.assertIsNotNone(first["next"])
        self.assertIsNotNone(second["previous"])
        self.assertEqual([item["id"] for item in first["results"] + second["results"]], expected)
        self.assertEqual(self.client.get(self.url, {"page": 3}).status_code, 404)

    def test_list_uses_frozen_names_and_totals(self):
        Venue.objects.filter(pk=self.venue.pk).update(name="Renamed")
        Product.objects.filter(pk=self.product.pk).update(name="Changed", sale_price=5000)
        row = self.client.get(self.url).data["results"][0]
        self.assertEqual(row["venue_name"], "Central")
        self.assertEqual(row["total"], 3000)
        self.assertEqual(row["method"], "CASH")
        self.assertNotIn("snapshot", row)

    def test_panel_has_no_write_or_cancellation_endpoints(self):
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(self.url, {}, format="json").status_code, 405)
        self.assertEqual(Invoice.objects.count(), 2)

    def issue_at(self, timestamp, venue=None):
        create = Payment.objects.create
        paid_at = datetime.fromisoformat(timestamp).replace(tzinfo=datetime_timezone.utc)
        with patch("apps.payments.services.Payment.objects.create", side_effect=lambda **kwargs: create(**kwargs, paid_at=paid_at)):
            return self.issue(venue or self.venue, Table.objects.count() + 1)

    def test_history_includes_both_edges_of_bogota_day_not_utc_day(self):
        before = self.issue_at("2026-10-25T04:59:59.999999")
        start = self.issue_at("2026-10-25T05:00:00")
        end = self.issue_at("2026-10-26T04:59:59.999999")
        after = self.issue_at("2026-10-26T05:00:00")
        rows = self.client.get(self.url, {"start_date": "2026-10-25", "end_date": "2026-10-25"}).data["results"]
        ids = {row["id"] for row in rows}
        self.assertTrue({start.pk, end.pk}.issubset(ids))
        self.assertTrue({before.pk, after.pk}.isdisjoint(ids))

    def test_history_dates_venue_and_number_combine_with_and(self):
        local = self.issue_at("2020-02-29T17:00:00")
        remote = self.issue_at("2020-02-29T18:00:00", self.other_venue)
        self.client.force_authenticate(self.admin)
        filters = {"start_date": "2020-02-29", "end_date": "2020-02-29", "venue": self.other_venue.pk, "number": remote.number.lower()}
        rows = self.client.get(self.url, filters).data["results"]
        self.assertEqual([row["id"] for row in rows], [remote.pk])
        self.assertEqual(self.client.get(self.url, {**filters, "number": local.number}).data["count"], 0)

    def test_combined_history_filters_cannot_escape_cashier_venue(self):
        remote = self.issue_at("2020-02-29T18:00:00", self.other_venue)
        filters = {"start_date": "2020-02-29", "end_date": "2020-02-29", "venue": self.other_venue.pk, "number": remote.number}
        self.assertEqual(self.client.get(self.url, filters).data["count"], 0)
        filters.pop("venue")
        self.assertEqual(self.client.get(self.url, filters).data["count"], 0)

    def test_history_allows_single_date_bounds(self):
        old = self.issue_at("2010-01-01T17:00:00")
        self.assertEqual([row["id"] for row in self.client.get(self.url, {"end_date": "2010-01-01"}).data["results"]], [old.pk])
        rows = self.client.get(self.url, {"start_date": "2010-01-02"}).data["results"]
        self.assertNotIn(old.pk, [row["id"] for row in rows])

    def test_history_keeps_old_records_without_implicit_date_limit(self):
        old = self.issue_at("2010-01-01T17:00:00")
        ids = [row["id"] for row in self.client.get(self.url).data["results"]]
        self.assertIn(old.pk, ids)

    def test_history_rejects_invalid_and_reversed_dates(self):
        for params in ({"start_date": "not-a-date"}, {"end_date": "2026-02-29"},
                       {"start_date": "2026-10-26", "end_date": "2026-10-25"},
                       {"start_date": "2026-10-25T12:00:00Z"}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url, params).status_code, 400)

    def test_history_partial_number_is_case_insensitive_and_literal(self):
        rows = self.client.get(self.url, {"number": self.local.number.lower()[1:]}).data["results"]
        self.assertEqual([row["id"] for row in rows], [self.local.pk])
        for number in ("%", "_", "no-such-receipt"):
            self.assertEqual(self.client.get(self.url, {"number": number}).data["count"], 0)
        self.assertEqual(self.client.get(self.url, {"number": "x" * 61}).status_code, 400)

    def test_history_maximum_end_date_does_not_overflow(self):
        self.assertEqual(self.client.get(self.url, {"end_date": "9999-12-31"}).data["count"], 1)
