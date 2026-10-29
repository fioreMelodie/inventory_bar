from datetime import timedelta

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.authentication.models import UserSession
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderStatus
from apps.tables.models import Table, TableStatus


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WorkflowRegressionTests(APITestCase):
    def setUp(self):
        self.venue = Venue.objects.create(name="Test venue")
        self.other_venue = Venue.objects.create(name="Other venue")
        self.waiter = User.objects.create_user(
            username="waiter", password="TestPassword2026*", full_name="Test waiter",
            role=Role.WAITER, venue=self.venue,
        )
        self.other_waiter = User.objects.create_user(
            username="other", password="TestPassword2026*", full_name="Other waiter",
            role=Role.WAITER, venue=self.venue,
        )
        self.table = Table.objects.create(venue=self.venue, identifier="T1")
        self.product = Product.objects.create(
            name="Test product", product_type="Food", category="Food",
            purchase_price=1000, sale_price=2000,
        )
        Stock.objects.create(venue=self.venue, product=self.product, quantity=10)
        login = self.client.post(reverse("authentication:login"), {
            "username": self.waiter.username, "password": "TestPassword2026*",
        }, format="json")
        self.session = UserSession.objects.get(pk=login.data["session_id"])
        self.refresh = login.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def open_order(self):
        response = self.client.post(reverse("orders:order-list"), {
            "table": self.table.pk,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data["id"]

    def test_room_keeps_order_and_elapsed_time_after_sending_to_cashier(self):
        order_id = self.open_order()
        self.client.post(reverse("orders:order-add-item", args=[order_id]), {
            "product": self.product.pk, "quantity": 2,
        }, format="json")
        self.client.post(reverse("orders:order-send-to-cashier", args=[order_id]))
        response = self.client.get(reverse("tables:table-room"))
        row = response.data["results"][0]
        self.assertEqual(row["active_order"], order_id)
        self.assertIsNotNone(row["occupied_minutes"])

    def test_cannot_retrieve_a_table_from_another_venue(self):
        table = Table.objects.create(venue=self.other_venue, identifier="T2")
        response = self.client.get(reverse("tables:table-detail", args=[table.pk]))
        self.assertEqual(response.status_code, 404)

    def test_role_and_venue_changes_wait_for_the_next_login(self):
        User.objects.filter(pk=self.waiter.pk).update(role=Role.CASHIER, venue=self.other_venue)
        response = self.client.get(reverse("authentication:current-user"))
        self.assertEqual(response.data["role"], Role.WAITER)
        self.assertEqual(response.data["venue"], self.venue.pk)
        self.open_order()
        login = self.client.post(reverse("authentication:login"), {
            "username": self.waiter.username, "password": "TestPassword2026*",
        }, format="json")
        self.assertEqual(login.data["user"]["role"], Role.CASHIER)
        self.assertEqual(login.data["user"]["venue"], self.other_venue.pk)

    def test_background_polling_does_not_extend_inactivity(self):
        previous = timezone.now() - timedelta(minutes=2)
        UserSession.objects.filter(pk=self.session.pk).update(last_activity_at=previous)
        response = self.client.get(
            reverse("tables:table-room"), HTTP_X_SESSION_ACTIVITY="background",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.last_activity_at, previous)

    def test_cannot_open_an_order_at_an_inactive_venue(self):
        Venue.objects.filter(pk=self.venue.pk).update(is_active=False)
        response = self.client.post(reverse("orders:order-list"), {
            "table": self.table.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_another_waiter_cannot_cancel_my_order(self):
        self.table.status = TableStatus.OCCUPIED
        self.table.save()
        order = Order.objects.create(
            venue=self.venue, table=self.table, waiter=self.other_waiter,
        )
        response = self.client.post(reverse("orders:order-cancel", args=[order.pk]))
        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.OPEN)

    def test_background_refresh_does_not_extend_inactivity(self):
        previous = timezone.now() - timedelta(minutes=2)
        UserSession.objects.filter(pk=self.session.pk).update(last_activity_at=previous)
        response = self.client.post(
            reverse("authentication:token-refresh"), {"refresh": self.refresh},
            format="json", HTTP_X_SESSION_ACTIVITY="background",
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.last_activity_at, previous)

    def test_background_request_cannot_use_an_expired_session(self):
        UserSession.objects.filter(pk=self.session.pk).update(
            last_activity_at=timezone.now() - timedelta(minutes=3),
        )
        response = self.client.get(
            reverse("tables:table-room"), HTTP_X_SESSION_ACTIVITY="background",
        )
        self.assertEqual(response.status_code, 401)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)

    def test_waiter_cannot_retrieve_an_inactive_product(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(reverse("catalog:product-detail", args=[self.product.pk]))
        self.assertEqual(response.status_code, 404)
