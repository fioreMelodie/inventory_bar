from datetime import datetime, timezone
from time import perf_counter
from unittest.mock import patch

from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.locations.models import Venue
from .models import AuditEvent, EventType
from .services import record_event


class AuditLogTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.central = Venue.objects.create(name="Central")
        cls.north = Venue.objects.create(name="North", is_active=False)
        cls.admin_user = User.objects.create_user(username="admin", full_name="Administrator", role=Role.ADMIN, is_staff=True, is_superuser=True)
        cls.cashier = User.objects.create_user(username="cashier", full_name="Cashier", role=Role.CASHIER, venue=cls.central)
        cls.waiter = User.objects.create_user(username="waiter", full_name="Waiter", role=Role.WAITER, venue=cls.central)
        cls.url = reverse("audit:event-list")

    def setUp(self):
        self.client.force_authenticate(self.admin_user)

    def event(self, *, username="cashier", venue=None, event_type=EventType.ORDER_OPENED,
              timestamp="2026-10-25T17:00:00", legacy=False, description="Opened order 1."):
        at = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        with patch("django.utils.timezone.now", return_value=at):
            if legacy:
                return AuditEvent.objects.create(username=username, event_type=event_type, description=description)
            return record_event(username=username, user=self.admin_user, event_type=event_type,
                                venue=venue, entity="Order", entity_id=1, description=description)

    def test_admin_can_list_and_view_complete_read_only_details(self):
        event = self.event(venue=self.north, description="Line one.\nLine two.")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        row = response.data["results"][0]
        self.assertEqual((row["username"], row["venue"], row["venue_name"]), ("cashier", self.north.pk, "North"))
        self.assertNotIn("description", row)
        detail = self.client.get(reverse("audit:event-detail", args=[event.pk]))
        self.assertEqual(detail.data["description"], "Line one.\nLine two.")
        self.assertEqual(detail.data["entity_id"], "1")
        self.assertEqual(detail["Cache-Control"], "no-store")
        self.assertTrue(any(item["value"] == EventType.PAYMENT_PROCESSED for item in response.data["event_types"]))

    def test_non_admin_and_anonymous_are_denied_even_for_known_ids(self):
        event = self.event(venue=self.central)
        for user, code in ((self.cashier, 403), (self.waiter, 403), (None, 401)):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(self.url).status_code, code)
            self.assertEqual(self.client.get(reverse("audit:event-detail", args=[event.pk])).status_code, code)

    def test_filters_combine_and_include_inactive_venues(self):
        target = self.event(venue=self.north)
        self.event(venue=self.central)
        self.event(venue=self.north, username="waiter")
        self.event(venue=self.north, event_type=EventType.PAYMENT_PROCESSED)
        self.event(venue=self.north, timestamp="2020-01-01T17:00:00")
        data = self.client.get(self.url, {"start_date": "2026-10-25", "end_date": "2026-10-25",
                                       "username": "CASH", "event_type": EventType.ORDER_OPENED, "venue": self.north.pk}).data
        self.assertEqual([row["id"] for row in data["results"]], [target.pk])

    def test_history_has_no_implicit_date_limit(self):
        old = self.event(timestamp="2010-01-01T17:00:00", legacy=True)
        self.assertEqual(self.client.get(self.url).data["results"][0]["id"], old.pk)

    def test_dates_use_bogota_day_boundaries(self):
        events = [self.event(timestamp=value) for value in (
            "2026-10-25T04:59:59.999999", "2026-10-25T05:00:00",
            "2026-10-26T04:59:59.999999", "2026-10-26T05:00:00")]
        rows = self.client.get(self.url, {"start_date": "2026-10-25", "end_date": "2026-10-25"}).data["results"]
        self.assertEqual([row["id"] for row in rows], [events[2].pk, events[1].pk])
        detail = self.client.get(reverse("audit:event-detail", args=[events[2].pk])).data
        self.assertIn("999999", detail["created_at"])

    def test_invalid_filters_are_rejected(self):
        for params in ({"start_date": "invalid"}, {"start_date": "2026-10-26", "end_date": "2026-10-25"},
                       {"event_type": "UNKNOWN"}, {"venue": "abc"}, {"venue": 0}, {"venue": 9223372036854775808}):
            self.assertEqual(self.client.get(self.url, params).status_code, 400)

    def test_legacy_unknown_and_new_unassociated_events_are_distinct(self):
        old = self.event(legacy=True)
        global_event = self.event()
        self.event(venue=self.central)
        old_rows = self.client.get(self.url, {"venue": "__unrecorded__"}).data["results"]
        global_rows = self.client.get(self.url, {"venue": "__none__"}).data["results"]
        self.assertEqual([row["id"] for row in old_rows], [old.pk])
        self.assertEqual([row["id"] for row in global_rows], [global_event.pk])
        self.assertFalse(old_rows[0]["venue_recorded"])
        self.assertTrue(global_rows[0]["venue_recorded"])

    def test_recorded_venue_name_and_username_do_not_follow_later_changes(self):
        event = self.event(venue=self.north)
        Venue.objects.filter(pk=self.north.pk).update(name="Renamed")
        User.objects.filter(pk=self.admin_user.pk).update(venue=self.central, username="changed-admin")
        event.refresh_from_db()
        self.assertEqual((event.venue_id, event.venue_name, event.username), (self.north.pk, "North", "cashier"))

    def test_events_are_immutable_in_models_api_and_django_admin(self):
        event = self.event(venue=self.central)
        detail = reverse("audit:event-detail", args=[event.pk])
        for method in ("post", "put", "patch", "delete"):
            self.assertEqual(getattr(self.client, method)(detail, {}, format="json").status_code, 405)
            self.assertEqual(getattr(self.client, method)(self.url, {}, format="json").status_code, 405)
        for action in (lambda: event.save(), lambda: event.delete(),
                       lambda: AuditEvent.objects.filter(pk=event.pk).update(description="changed"),
                       lambda: AuditEvent.objects.filter(pk=event.pk).delete()):
            with self.assertRaises(NotImplementedError):
                action()
        request = RequestFactory().get("/")
        request.user = self.admin_user
        model_admin = admin.site._registry[AuditEvent]
        self.assertTrue(model_admin.has_view_permission(request, event))
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, event))
        self.assertFalse(model_admin.has_delete_permission(request, event))
        request.user = self.cashier
        self.assertFalse(model_admin.has_view_permission(request, event))

    def test_detail_not_found_and_pagination_with_stable_ties(self):
        ids = [self.event().pk for _ in range(26)]
        first = self.client.get(self.url).data
        second = self.client.get(self.url, {"page": 2}).data
        self.assertEqual([row["id"] for row in first["results"] + second["results"]], list(reversed(ids)))
        self.assertEqual(self.client.get(self.url, {"page": 3}).status_code, 404)
        self.assertEqual(self.client.get(reverse("audit:event-detail", args=[999999])).status_code, 404)

    def test_record_event_keeps_venue_ip_and_all_supported_types(self):
        request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1")
        for value, _ in EventType.choices:
            event = record_event(event_type=value, username="admin", user=self.admin_user,
                                 venue=self.central, request=request)
            self.assertEqual((event.event_type, event.venue_name, event.ip_address), (value, "Central", "127.0.0.1"))

    def test_filter_performance_and_two_queries_for_5000_events(self):
        AuditEvent.objects.bulk_create([
            AuditEvent(username="cashier", event_type=EventType.ORDER_OPENED, venue=self.central,
                       venue_name="Central", venue_recorded=True, description="Order opened.")
            for _ in range(5000)
        ])
        # Use a wide range so this benchmark has no dependency on wall-clock day.
        started = perf_counter()
        with self.assertNumQueries(2):
            response = self.client.get(self.url, {"start_date": "2000-01-01", "end_date": "2099-12-31",
                                                 "username": "cash", "event_type": EventType.ORDER_OPENED,
                                                 "venue": self.central.pk})
        elapsed = perf_counter() - started
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5000)
        self.assertEqual(len(response.data["results"]), 25)
        self.assertLess(elapsed, 2.0)
        print(f"HU30 audit benchmark (5000 events, all filters): {elapsed:.3f}s")

    def test_inventory_and_venue_configuration_record_affected_venue(self):
        from apps.catalog.models import Product
        from apps.inventory.services import register_entry
        product = Product.objects.create(name="Coffee", product_type="Beverage", category="Coffee", purchase_price=1000, sale_price=3000)
        register_entry(venue=self.north, product=product, quantity=2, performed_by=self.admin_user)
        self.assertEqual(AuditEvent.objects.get(event_type=EventType.STOCK_ENTRY).venue_id, self.north.pk)
        response = self.client.post("/api/venues/", {"name": "New venue", "address": "Street 1"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        event = AuditEvent.objects.get(event_type=EventType.VENUE_CREATED)
        self.assertEqual((event.venue_id, event.venue_name), (response.data["id"], "New venue"))

    def test_login_and_logout_keep_session_venue_even_after_user_reassignment(self):
        self.cashier.set_password("Session.Test.2026**")
        self.cashier.save(update_fields=["password"])
        self.client.force_authenticate(None)
        response = self.client.post("/api/auth/login/", {"username": "cashier", "password": "Session.Test.2026**"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AuditEvent.objects.get(event_type=EventType.LOGIN_SUCCESS).venue_id, self.central.pk)
        User.objects.filter(pk=self.cashier.pk).update(venue=self.north)
        result = self.client.post("/api/auth/logout/", {"refresh": response.data["refresh"], "reason": "MANUAL"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(AuditEvent.objects.get(event_type=EventType.SESSION_LOGOUT).venue_id, self.central.pk)
        self.assertNotIn("Session.Test.2026", str(list(AuditEvent.objects.values_list("description", flat=True))))

    def test_user_edit_audit_uses_target_venue_not_admin_venue(self):
        response = self.client.patch(f"/api/users/{self.cashier.pk}/", {"full_name": "Updated cashier"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AuditEvent.objects.get(event_type=EventType.USER_UPDATED).venue_id, self.central.pk)
