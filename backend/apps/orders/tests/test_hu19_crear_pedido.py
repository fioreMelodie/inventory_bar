"""
Pruebas de la HU19 - Crear Pedido (Mesero).
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations.models import Venue
from apps.orders.models import Order, OrderStatus
from apps.tables.models import Table, TableStatus


class CreateOrderTests(APITestCase):
    """Validación de los criterios de aceptación de la HU19."""

    def setUp(self):
        self.url = reverse("orders:order-list")
        self.password = "Cafe2026*Bar"

        self.galeria = Venue.objects.create(name="Galería")
        self.zona_t = Venue.objects.create(name="Zona T")

        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.galeria,
        )

        self.mesa1 = Table.objects.create(venue=self.galeria, identifier="Mesa 1")
        self.mesa_otra_sede = Table.objects.create(venue=self.zona_t, identifier="Mesa 1")

        self.login(self.mesero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_mesero_abre_un_pedido_en_una_mesa_libre(self):
        """Se genera el pedido asociado a la mesa y al mesero."""
        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.table, self.mesa1)
        self.assertEqual(order.waiter, self.mesero)
        self.assertEqual(order.venue, self.galeria)

    def test_el_pedido_queda_en_estado_abierto(self):
        """El pedido se crea en estado ABIERTO."""
        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.data["status"], OrderStatus.OPEN)
        self.assertTrue(Order.objects.get(id=response.data["id"]).is_open)

    def test_se_registra_la_fecha_y_hora_de_apertura(self):
        """Queda constancia de cuándo se abrió el pedido."""
        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertIsNotNone(response.data["opened_at"])
        self.assertIsNotNone(Order.objects.get(id=response.data["id"]).opened_at)

    def test_el_pedido_recibe_un_identificador_unico(self):
        """Cada pedido tiene su propio ID."""
        primero = self.client.post(self.url, {"table": self.mesa1.id}, format="json")
        mesa2 = Table.objects.create(venue=self.galeria, identifier="Mesa 2")
        segundo = self.client.post(self.url, {"table": mesa2.id}, format="json")

        self.assertNotEqual(primero.data["id"], segundo.data["id"])

    def test_la_mesa_pasa_a_ocupada(self):
        """La mesa cambia automáticamente de estado al abrir el pedido."""
        self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.mesa1.refresh_from_db()
        self.assertEqual(self.mesa1.status, TableStatus.OCCUPIED)

    def test_no_se_puede_abrir_un_pedido_en_una_mesa_ocupada(self):
        """Solo se puede crear un pedido si la mesa está LIBRE."""
        self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.filter(table=self.mesa1).count(), 1)

    def test_una_mesa_solo_tiene_un_pedido_activo(self):
        """La restricción de unicidad lo garantiza a nivel de base de datos."""
        self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        abiertos = Order.objects.filter(table=self.mesa1, status=OrderStatus.OPEN)
        self.assertEqual(abiertos.count(), 1)

    def test_el_mesero_no_puede_abrir_pedidos_en_otra_sede(self):
        """El alcance por sede también aplica a los pedidos."""
        response = self.client.post(
            self.url, {"table": self.mesa_otra_sede.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_no_se_abren_pedidos_en_mesas_inactivas(self):
        """Una mesa retirada de la operación no admite pedidos."""
        inactiva = Table.objects.create(
            venue=self.galeria, identifier="Mesa 9", is_active=False
        )

        response = self.client.post(self.url, {"table": inactiva.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_cajero_no_abre_pedidos(self):
        """Tomar pedidos corresponde al Mesero y al Administrador."""
        self.login(self.cajero)

        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_administrador_puede_operar_como_mesero(self):
        """El Administrador asume el rol de mesero cuando se requiere."""
        self.login(self.admin)

        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_el_pedido_nace_con_total_en_cero(self):
        """Todavía no tiene ítems."""
        response = self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        self.assertEqual(response.data["total"], 0)

    def test_el_cajero_puede_consultar_los_pedidos_de_su_sede(self):
        """La consulta está disponible para los tres roles."""
        self.client.post(self.url, {"table": self.mesa1.id}, format="json")
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_la_apertura_queda_en_el_log_de_auditoria(self):
        """Se registra la apertura con mesa y sede."""
        self.client.post(self.url, {"table": self.mesa1.id}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.ORDER_OPENED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.mesero)
        self.assertIn("Mesa 1", evento.description)
        self.assertIn("Galería", evento.description)
