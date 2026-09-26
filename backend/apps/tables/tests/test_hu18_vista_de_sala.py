"""
Pruebas de la HU18 - Consultar Vista de Sala (Estado de Mesas).
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.locations.models import Venue
from apps.orders.models import Order, OrderStatus
from apps.tables.models import Table, TableStatus


class RoomViewTests(APITestCase):
    """Validación de los criterios de aceptación de la HU18."""

    def setUp(self):
        self.url = reverse("tables:table-room")
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
        self.mesa2 = Table.objects.create(venue=self.galeria, identifier="Mesa 2")
        self.mesa_zona_t = Table.objects.create(venue=self.zona_t, identifier="Mesa 1")

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def occupy(self, table, minutes_ago=0):
        """Abre un pedido en la mesa y la marca como ocupada."""
        order = Order.objects.create(
            venue=table.venue, table=table, waiter=self.mesero, status=OrderStatus.OPEN
        )
        if minutes_ago:
            Order.objects.filter(id=order.id).update(
                opened_at=timezone.now() - timedelta(minutes=minutes_ago)
            )
        table.status = TableStatus.OCCUPIED
        table.save(update_fields=["status"])
        return order

    def row(self, response, identifier):
        return next(
            item for item in response.data["results"] if item["identifier"] == identifier
        )

    def test_la_vista_muestra_todas_las_mesas_de_la_sede(self):
        """El usuario ve el estado actual del salón."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        identificadores = sorted(item["identifier"] for item in response.data["results"])
        self.assertEqual(identificadores, ["Mesa 1", "Mesa 2"])

    def test_distingue_mesas_libres_y_ocupadas(self):
        """El estado permite diferenciarlas visualmente."""
        self.occupy(self.mesa1)
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertEqual(self.row(response, "Mesa 1")["status"], TableStatus.OCCUPIED)
        self.assertEqual(self.row(response, "Mesa 2")["status"], TableStatus.FREE)

    def test_una_mesa_ocupada_muestra_el_tiempo_transcurrido(self):
        """Se informa cuánto lleva abierta la orden."""
        self.occupy(self.mesa1, minutes_ago=25)
        self.login(self.mesero)

        response = self.client.get(self.url)

        fila = self.row(response, "Mesa 1")
        self.assertEqual(fila["occupied_minutes"], 25)
        self.assertIsNotNone(fila["occupied_since"])

    def test_una_mesa_libre_no_tiene_tiempo_transcurrido(self):
        """Sin pedido activo no hay tiempo que mostrar."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        fila = self.row(response, "Mesa 2")
        self.assertIsNone(fila["occupied_minutes"])
        self.assertIsNone(fila["active_order"])

    def test_la_mesa_ocupada_expone_su_pedido_activo(self):
        """El Cajero puede consultar el pedido activo de una mesa ocupada."""
        order = self.occupy(self.mesa1)
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertEqual(self.row(response, "Mesa 1")["active_order"], order.id)

    def test_el_mesero_solo_ve_las_mesas_de_su_sede(self):
        """El alcance por sede aplica a la vista de sala."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertEqual(response.data["venue_name"], "Galería")
        identificadores = [item["identifier"] for item in response.data["results"]]
        self.assertEqual(len(identificadores), 2)

    def test_el_cajero_no_puede_ver_otra_sede(self):
        """Aunque pida otra sede, recibe la suya."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertEqual(response.data["venue_name"], "Galería")

    def test_el_administrador_consulta_cualquier_sede(self):
        """Solo el Administrador ve las mesas de todas las sedes."""
        self.login(self.admin)

        response = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertEqual(response.data["venue_name"], "Zona T")
        self.assertEqual(len(response.data["results"]), 1)

    def test_las_mesas_inactivas_no_aparecen_en_la_sala(self):
        """Una mesa retirada de la operación no se muestra."""
        Table.objects.create(venue=self.galeria, identifier="Mesa 9", is_active=False)
        self.login(self.mesero)

        response = self.client.get(self.url)

        identificadores = [item["identifier"] for item in response.data["results"]]
        self.assertNotIn("Mesa 9", identificadores)

    def test_el_estado_se_refleja_sin_pasos_intermedios(self):
        """Al abrir un pedido, la siguiente consulta ya muestra la mesa ocupada."""
        self.login(self.mesero)
        self.assertEqual(
            self.row(self.client.get(self.url), "Mesa 1")["status"], TableStatus.FREE
        )

        self.client.post(reverse("orders:order-list"), {"table": self.mesa1.id}, format="json")

        self.assertEqual(
            self.row(self.client.get(self.url), "Mesa 1")["status"], TableStatus.OCCUPIED
        )

    def test_no_se_abre_un_pedido_en_una_mesa_ocupada(self):
        """Desde la vista de sala no se puede ocupar dos veces la misma mesa."""
        self.occupy(self.mesa1)
        self.login(self.mesero)

        response = self.client.post(
            reverse("orders:order-list"), {"table": self.mesa1.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_vista_de_sala_exige_autenticacion(self):
        """La sala no es pública."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
