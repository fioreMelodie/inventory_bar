"""
Pruebas de la HU22 - Consultar Pedidos Activos (Cajero).
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class CashierPanelTests(APITestCase):
    """Validación de los criterios de aceptación de la HU22."""

    def setUp(self):
        self.url = reverse("orders:order-list")
        self.password = "Cafe2026*Bar"

        self.galeria = Venue.objects.create(name="Galería")
        self.zona_t = Venue.objects.create(name="Zona T")

        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )
        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.galeria,
        )
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.mesero_zona_t = User.objects.create_user(
            username="mesero2", password=self.password,
            full_name="Sofía Cardona", role=Role.WAITER, venue=self.zona_t,
        )

        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def build_order(self, venue, waiter, identifier, *, in_cashier=True, minutes_ago=0):
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=waiter)
        OrderItem.objects.create(
            order=order, product=self.cerveza, quantity=2, unit_price=9000
        )
        order.recalculate_total()

        if in_cashier:
            order.status = OrderStatus.IN_CASHIER
            order.sent_to_cashier_at = timezone.now() - timedelta(minutes=minutes_ago)
            order.save(update_fields=["status", "sent_to_cashier_at"])

        return order

    def pending(self):
        return self.client.get(self.url, {"status": OrderStatus.IN_CASHIER}).data["results"]

    def test_el_cajero_ve_los_pedidos_enviados_a_su_sede(self):
        """El panel muestra los pedidos en estado EN_CAJA."""
        enviado = self.build_order(self.galeria, self.mesero, "Mesa 1")
        self.login(self.cajero)

        resultados = self.pending()

        self.assertEqual([item["id"] for item in resultados], [enviado.id])

    def test_el_panel_no_muestra_pedidos_abiertos(self):
        """Un pedido que el mesero aún no envió no corresponde a caja."""
        self.build_order(self.galeria, self.mesero, "Mesa 1", in_cashier=False)
        self.login(self.cajero)

        self.assertEqual(self.pending(), [])

    def test_solo_se_muestran_pedidos_de_la_sede_del_cajero(self):
        """El alcance por sede aplica al panel de caja."""
        propio = self.build_order(self.galeria, self.mesero, "Mesa 1")
        self.build_order(self.zona_t, self.mesero_zona_t, "Mesa 1")
        self.login(self.cajero)

        resultados = self.pending()

        self.assertEqual([item["id"] for item in resultados], [propio.id])

    def test_el_administrador_ve_los_pedidos_de_todas_las_sedes(self):
        """El Administrador no está limitado a una sede."""
        self.build_order(self.galeria, self.mesero, "Mesa 1")
        self.build_order(self.zona_t, self.mesero_zona_t, "Mesa 1")
        self.login(self.admin)

        self.assertEqual(len(self.pending()), 2)

    def test_el_administrador_puede_filtrar_por_sede(self):
        """Puede concentrarse en una sede concreta."""
        self.build_order(self.galeria, self.mesero, "Mesa 1")
        zona = self.build_order(self.zona_t, self.mesero_zona_t, "Mesa 1")
        self.login(self.admin)

        respuesta = self.client.get(
            self.url, {"status": OrderStatus.IN_CASHIER, "venue": self.zona_t.id}
        )

        self.assertEqual([item["id"] for item in respuesta.data["results"]], [zona.id])

    def test_los_pedidos_se_ordenan_por_hora_de_envio(self):
        """Se atienden en orden de llegada."""
        primero = self.build_order(self.galeria, self.mesero, "Mesa 1", minutes_ago=30)
        segundo = self.build_order(self.galeria, self.mesero, "Mesa 2", minutes_ago=10)
        tercero = self.build_order(self.galeria, self.mesero, "Mesa 3", minutes_ago=1)
        self.login(self.cajero)

        resultados = [item["id"] for item in self.pending()]

        self.assertEqual(resultados, [primero.id, segundo.id, tercero.id])

    def test_el_panel_informa_los_datos_necesarios_para_el_cobro(self):
        """Número de pedido, mesa, mesero, total y hora de envío."""
        self.build_order(self.galeria, self.mesero, "Mesa 1")
        self.login(self.cajero)

        pedido = self.pending()[0]

        self.assertIn("id", pedido)
        self.assertEqual(pedido["table_identifier"], "Mesa 1")
        self.assertEqual(pedido["waiter_name"], "Juan Pérez")
        self.assertEqual(pedido["total"], 18000)
        self.assertIsNotNone(pedido["sent_to_cashier_at"])

    def test_el_detalle_del_pedido_incluye_los_items(self):
        """Desde el panel se consulta el detalle para procesar el cobro."""
        pedido = self.build_order(self.galeria, self.mesero, "Mesa 1")
        self.login(self.cajero)

        respuesta = self.client.get(reverse("orders:order-detail", args=[pedido.id]))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(respuesta.data["items"]), 1)
        self.assertEqual(respuesta.data["items"][0]["quantity"], 2)

    def test_el_mesero_no_ve_el_panel_de_otra_sede(self):
        """El alcance por sede se respeta para todos los roles."""
        self.build_order(self.zona_t, self.mesero_zona_t, "Mesa 1")
        self.login(self.mesero)

        self.assertEqual(self.pending(), [])

    def test_el_panel_exige_autenticacion(self):
        """No es una vista pública."""
        respuesta = self.client.get(self.url, {"status": OrderStatus.IN_CASHIER})

        self.assertEqual(respuesta.status_code, status.HTTP_401_UNAUTHORIZED)
