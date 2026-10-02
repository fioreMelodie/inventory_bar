"""
Pruebas de la HU21 - Enviar Pedido a Caja.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class SendOrderToCashierTests(APITestCase):
    """Validación de los criterios de aceptación de la HU21."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")

        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.otro_mesero = User.objects.create_user(
            username="mesero2", password=self.password,
            full_name="Pedro Díaz", role=Role.WAITER, venue=self.galeria,
        )
        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.galeria,
        )

        self.mesa = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)

        self.order = Order.objects.create(
            venue=self.galeria, table=self.mesa, waiter=self.mesero
        )
        OrderItem.objects.create(
            order=self.order, product=self.cerveza, quantity=3, unit_price=9000
        )
        self.order.recalculate_total()

        self.url = reverse("orders:order-send-to-cashier", args=[self.order.id])
        self.login(self.mesero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_pedido_cambia_a_estado_en_caja(self):
        """El estado pasa de ABIERTO a EN_CAJA."""
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_CASHIER)

    def test_se_registra_la_hora_de_envio(self):
        """Queda constancia de cuándo se trasladó el pedido a caja."""
        self.client.post(self.url, {}, format="json")

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.sent_to_cashier_at)

    def test_no_se_envia_un_pedido_sin_items(self):
        """Solo se envían a caja pedidos con al menos un ítem."""
        vacio = Order.objects.create(
            venue=self.galeria,
            table=Table.objects.create(venue=self.galeria, identifier="Mesa 2"),
            waiter=self.mesero,
        )

        response = self.client.post(
            reverse("orders:order-send-to-cashier", args=[vacio.id]), {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        vacio.refresh_from_db()
        self.assertEqual(vacio.status, OrderStatus.OPEN)

    def test_el_pedido_enviado_es_inmutable(self):
        """No se pueden agregar más productos tras el envío."""
        self.client.post(self.url, {}, format="json")

        response = self.client.post(
            reverse("orders:order-add-item", args=[self.order.id]),
            {"product": self.cerveza.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(OrderItem.objects.filter(order=self.order).count(), 1)

    def test_un_pedido_enviado_tampoco_se_cancela(self):
        """La inmutabilidad alcanza también a la cancelación."""
        self.client.post(self.url, {}, format="json")

        response = self.client.post(
            reverse("orders:order-cancel", args=[self.order.id]), {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_envia_dos_veces_el_mismo_pedido(self):
        """Solo se envían a caja pedidos en estado ABIERTO."""
        self.client.post(self.url, {}, format="json")

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_mesero_sigue_viendo_el_pedido_en_modo_lectura(self):
        """Puede consultarlo, pero ya no editarlo."""
        self.client.post(self.url, {}, format="json")

        response = self.client.get(reverse("orders:order-detail", args=[self.order.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], OrderStatus.IN_CASHIER)
        self.assertEqual(len(response.data["items"]), 1)

    def test_el_cajero_ve_el_pedido_en_su_panel(self):
        """El pedido queda visible para el Cajero al ser enviado."""
        self.client.post(self.url, {}, format="json")
        self.login(self.cajero)

        response = self.client.get(
            reverse("orders:order-list"), {"status": OrderStatus.IN_CASHIER}
        )

        identificadores = [item["id"] for item in response.data["results"]]
        self.assertIn(self.order.id, identificadores)

    def test_antes_del_envio_el_pedido_no_esta_en_el_panel_de_caja(self):
        """El panel del cajero solo muestra lo que ya fue enviado."""
        self.login(self.cajero)

        response = self.client.get(
            reverse("orders:order-list"), {"status": OrderStatus.IN_CASHIER}
        )

        self.assertEqual(len(response.data["results"]), 0)

    def test_un_mesero_no_envia_el_pedido_de_otro(self):
        """Cada mesero gestiona sus propios pedidos."""
        self.login(self.otro_mesero)

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_mesa_sigue_ocupada_tras_el_envio(self):
        """La mesa se libera al registrarse el pago, no al enviar a caja."""
        self.client.post(self.url, {}, format="json")

        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.status, TableStatus.OCCUPIED)

    def test_el_envio_queda_en_el_log_de_auditoria(self):
        """Se registra el envío con la mesa y el total."""
        self.client.post(self.url, {}, format="json")

        evento = AuditEvent.objects.filter(
            event_type=EventType.ORDER_SENT_TO_CASHIER
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.mesero)
        self.assertIn("Mesa 1", evento.description)
        self.assertIn("27000", evento.description)
