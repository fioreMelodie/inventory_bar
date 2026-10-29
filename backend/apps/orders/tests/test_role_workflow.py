from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderStatus
from apps.tables.models import Table, TableStatus


class RoleWorkflowTests(APITestCase):
    """Recorrido integrado con datos exclusivos de la base temporal de pruebas."""

    def setUp(self):
        self.password = "Workflow.2026*"
        self.venue = Venue.objects.create(name="Central")
        self.other_venue = Venue.objects.create(name="North")
        self.admin = self.account("administrator", Role.ADMIN)
        self.waiter = self.account("waiter", Role.WAITER, self.venue)
        self.cashier = self.account("cashier", Role.CASHIER, self.venue)
        self.other_waiter = self.account("other-waiter", Role.WAITER, self.venue)
        self.other_cashier = self.account("other-cashier", Role.CASHIER, self.other_venue)
        self.admin_client = self.login(self.admin)
        self.waiter_client = self.login(self.waiter)
        self.cashier_client = self.login(self.cashier)

        response = self.admin_client.post(
            reverse("catalog:product-list"),
            {"name": "Coffee", "product_type": "Beverage", "category": "Coffee",
             "purchase_price": 1000, "sale_price": 3000},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.product_id = response.data["id"]
        response = self.admin_client.post(
            reverse("tables:table-list"),
            {"venue": self.venue.id, "identifier": "Table 1"}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.table_id = response.data["id"]
        response = self.cashier_client.post(
            reverse("inventory:stock-entry"),
            {"product": self.product_id, "quantity": 20}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def account(self, username, role, venue=None):
        return User.objects.create_user(
            username=username, password=self.password,
            full_name=username, role=role, venue=venue,
        )

    def login(self, user):
        client = APIClient()
        response = client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return client

    def open_with_coffee(self):
        response = self.waiter_client.post(
            reverse("orders:order-list"), {"table": self.table_id}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        order_id = response.data["id"]
        response = self.waiter_client.post(
            reverse("orders:order-add-item", args=[order_id]),
            {"product": self.product_id, "quantity": 3}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["total"], 9000)
        self.assertEqual(Stock.objects.get(venue=self.venue, product_id=self.product_id).quantity, 17)
        return order_id

    def test_admin_inventory_waiter_and_cashier_handoff(self):
        product_url = reverse("catalog:product-detail", args=[self.product_id])
        self.assertIn("purchase_price", self.admin_client.get(product_url).data)
        for client in (self.waiter_client, self.cashier_client):
            self.assertNotIn("purchase_price", client.get(product_url).data)
            response = client.patch(product_url, {"sale_price": 4000}, format="json")
            self.assertEqual(response.status_code, 403)

        order_id = self.open_with_coffee()
        add_url = reverse("orders:order-add-item", args=[order_id])
        send_url = reverse("orders:order-send-to-cashier", args=[order_id])
        detail_url = reverse("orders:order-detail", args=[order_id])
        self.assertEqual(
            self.login(self.other_waiter).post(
                add_url, {"product": self.product_id, "quantity": 1}, format="json",
            ).status_code, 403,
        )
        self.assertEqual(self.cashier_client.post(send_url, {}, format="json").status_code, 403)
        self.assertEqual(
            self.cashier_client.get(reverse("orders:order-list"), {"status": "IN_CASHIER"}).data["count"], 0,
        )

        response = self.waiter_client.post(send_url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], OrderStatus.IN_CASHIER)
        pending = self.cashier_client.get(reverse("orders:order-list"), {"status": "IN_CASHIER"})
        self.assertEqual([row["id"] for row in pending.data["results"]], [order_id])
        self.assertEqual(pending.data["results"][0]["total"], 9000)
        self.assertEqual(self.login(self.other_cashier).get(detail_url).status_code, 404)
        self.assertEqual(self.admin_client.get(detail_url).status_code, 200)
        self.assertEqual(
            self.waiter_client.post(
                add_url, {"product": self.product_id, "quantity": 1}, format="json",
            ).status_code, 400,
        )
        self.assertEqual(
            self.waiter_client.post(
                reverse("orders:order-cancel", args=[order_id]), {}, format="json",
            ).status_code, 400,
        )
        room = self.waiter_client.get(reverse("tables:table-room"))
        table = next(row for row in room.data["results"] if row["id"] == self.table_id)
        self.assertEqual(table["status"], TableStatus.OCCUPIED)
        self.assertEqual(table["active_order_status"], OrderStatus.IN_CASHIER)
        self.assertEqual(Stock.objects.get(venue=self.venue, product_id=self.product_id).quantity, 17)
        self.assertTrue(AuditEvent.objects.filter(
            event_type=EventType.ORDER_SENT_TO_CASHIER, entity_id=str(order_id),
        ).exists())

    def test_cancel_restores_stock_and_frees_table(self):
        order_id = self.open_with_coffee()
        response = self.waiter_client.post(
            reverse("orders:order-cancel", args=[order_id]), {}, format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Order.objects.get(pk=order_id).status, OrderStatus.CANCELLED)
        self.assertEqual(Table.objects.get(pk=self.table_id).status, TableStatus.FREE)
        self.assertEqual(Stock.objects.get(venue=self.venue, product_id=self.product_id).quantity, 20)
        room = self.waiter_client.get(reverse("tables:table-room"))
        table = next(row for row in room.data["results"] if row["id"] == self.table_id)
        self.assertIsNone(table["active_order"])
        self.assertIsNone(table["active_order_status"])
        self.assertEqual(
            self.cashier_client.get(reverse("orders:order-list"), {"status": "IN_CASHIER"}).data["count"], 0,
        )
