from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table


class PendingOrdersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.venue = Venue.objects.create(name="Central")
        cls.other_venue = Venue.objects.create(name="North")
        cls.cashier = User.objects.create_user(
            username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.venue,
        )
        cls.admin = User.objects.create_user(
            username="admin", full_name="Administrator", role=Role.ADMIN,
        )
        cls.waiter = User.objects.create_user(
            username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.venue,
        )
        cls.product = Product.objects.create(
            name="Coffee", product_type="Beverage", category="Coffee",
            purchase_price=1000, sale_price=3000,
        )
        now = timezone.now()
        cls.first = cls.make_order(cls.venue, "1", now - timedelta(minutes=10), now)
        cls.second = cls.make_order(cls.venue, "2", now - timedelta(minutes=5), now - timedelta(hours=1))
        cls.other = cls.make_order(cls.other_venue, "3", now - timedelta(minutes=8), now)
        cls.open_order = cls.make_order(cls.venue, "4", None, now, OrderStatus.OPEN)
        cls.cancelled = cls.make_order(cls.venue, "5", None, now, OrderStatus.CANCELLED)

    @classmethod
    def make_order(cls, venue, identifier, sent_at, opened_at, status=OrderStatus.IN_CASHIER):
        table = Table.objects.create(venue=venue, identifier=identifier)
        order = Order.objects.create(
            venue=venue, table=table, waiter=cls.waiter, status=status,
            sent_to_cashier_at=sent_at, opened_at=opened_at, total=6000,
        )
        OrderItem.objects.create(order=order, product=cls.product, quantity=2, unit_price=3000)
        return order

    def setUp(self):
        self.url = reverse("orders:order-pending")
        self.client.force_authenticate(self.cashier)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_waiter_cannot_access_queue(self):
        self.client.force_authenticate(self.waiter)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_cashier_only_sees_own_venue_and_only_pending(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.first.id, self.second.id])

    def test_cashier_cannot_switch_venue_with_query_parameter(self):
        response = self.client.get(self.url, {"venue": self.other_venue.id})
        self.assertEqual([row["id"] for row in response.data["results"]], [self.first.id, self.second.id])

    def test_admin_sees_all_venues_in_sent_order_not_opened_order(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [self.first.id, self.other.id, self.second.id],
        )

    def test_admin_can_filter_venue(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url, {"venue": self.other_venue.id})
        self.assertEqual([row["id"] for row in response.data["results"]], [self.other.id])

    def test_invalid_venue_returns_validation_error(self):
        self.client.force_authenticate(self.admin)
        for venue in ("invalid", -1, 999999):
            with self.subTest(venue=venue):
                response = self.client.get(self.url, {"venue": venue})
                self.assertEqual(response.status_code, 400)
                self.assertIn("venue", response.data)

    def test_response_contains_all_cashier_detail_fields(self):
        row = self.client.get(self.url).data["results"][0]
        self.assertEqual(row["table_identifier"], "1")
        self.assertEqual(row["waiter_name"], "Waiter")
        self.assertEqual(row["total"], 6000)
        self.assertIsNotNone(row["sent_to_cashier_at"])
        self.assertEqual(row["items"][0]["quantity"], 2)
        self.assertEqual(row["items"][0]["product_name"], "Coffee")
        self.assertEqual(row["items"][0]["subtotal"], 6000)

    def test_same_timestamp_has_stable_id_order_and_missing_time_is_last(self):
        Order.objects.filter(pk=self.second.id).update(sent_to_cashier_at=self.first.sent_to_cashier_at)
        missing = self.make_order(self.venue, "6", None, timezone.now())
        response = self.client.get(self.url)
        self.assertEqual(
            [row["id"] for row in response.data["results"]],
            [self.first.id, self.second.id, missing.id],
        )

    def test_newly_sent_order_appears_on_next_read(self):
        self.client.force_authenticate(self.waiter)
        response = self.client.post(
            reverse("orders:order-send-to-cashier", args=[self.open_order.id]), {}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(self.cashier)
        rows = self.client.get(self.url).data["results"]
        self.assertEqual(rows[-1]["id"], self.open_order.id)

    def test_removed_from_pending_state_disappears(self):
        Order.objects.filter(pk=self.first.id).update(status=OrderStatus.CANCELLED)
        rows = self.client.get(self.url).data["results"]
        self.assertEqual([row["id"] for row in rows], [self.second.id])

    def test_queue_is_paginated_and_not_limited_to_dashboard_eight(self):
        for index in range(30):
            self.make_order(self.venue, f"Extra {index}", timezone.now(), timezone.now())
        response = self.client.get(self.url)
        self.assertEqual(response.data["count"], 32)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(len(response.data["results"]), 25)
        second_page = self.client.get(self.url, {"page": 2})
        self.assertEqual(len(second_page.data["results"]), 7)
