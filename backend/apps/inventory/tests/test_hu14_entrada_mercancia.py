"""
Pruebas de la HU14 - Registrar Entrada de Mercancía al Inventario.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import MovementType, Stock, StockMovement
from apps.locations.models import Venue


class StockEntryTests(APITestCase):
    """Validación de los criterios de aceptación de la HU14."""

    def setUp(self):
        self.url = reverse("inventory:stock-entry")
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

    def test_el_cajero_registra_una_entrada_en_su_sede(self):
        """La cantidad recibida se suma al stock de la sede."""
        self.login(self.cajero)

        response = self.client.post(
            self.url, {"product": self.cerveza.id, "quantity": 24}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stock = Stock.objects.get(venue=self.galeria, product=self.cerveza)
        self.assertEqual(stock.quantity, 24)

    def test_las_entradas_sucesivas_se_acumulan(self):
        """El stock suma cada entrada registrada."""
        self.login(self.cajero)

        self.client.post(self.url, {"product": self.cerveza.id, "quantity": 24}, format="json")
        self.client.post(self.url, {"product": self.cerveza.id, "quantity": 12}, format="json")

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 36
        )

    def test_el_stock_es_independiente_por_sede(self):
        """Cada sede mantiene su propio nivel de inventario."""
        self.login(self.cajero)
        self.client.post(self.url, {"product": self.cerveza.id, "quantity": 24}, format="json")

        self.login(self.admin)
        self.client.post(
            self.url,
            {"venue": self.zona_t.id, "product": self.cerveza.id, "quantity": 10},
            format="json",
        )

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 24
        )
        self.assertEqual(
            Stock.objects.get(venue=self.zona_t, product=self.cerveza).quantity, 10
        )

    def test_el_administrador_registra_entradas_en_cualquier_sede(self):
        """El Administrador gestiona el inventario de todas las sedes."""
        self.login(self.admin)

        response = self.client.post(
            self.url,
            {"venue": self.zona_t.id, "product": self.cerveza.id, "quantity": 48},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Stock.objects.get(venue=self.zona_t, product=self.cerveza).quantity, 48
        )

    def test_el_administrador_debe_indicar_la_sede(self):
        """Sin sede explícita la entrada del Administrador es ambigua."""
        self.login(self.admin)

        response = self.client.post(
            self.url, {"product": self.cerveza.id, "quantity": 10}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("venue", response.data)

    def test_el_cajero_no_puede_registrar_en_otra_sede(self):
        """El Cajero solo registra entradas en su sede asignada."""
        self.login(self.cajero)

        response = self.client.post(
            self.url,
            {"venue": self.zona_t.id, "product": self.cerveza.id, "quantity": 10},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Stock.objects.filter(venue=self.zona_t).exists())

    def test_el_mesero_no_gestiona_inventario(self):
        """El Mesero no registra entradas de mercancía."""
        self.login(self.mesero)

        response = self.client.post(
            self.url, {"product": self.cerveza.id, "quantity": 10}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_cantidad_debe_ser_mayor_que_cero(self):
        """No se admiten cantidades nulas ni negativas."""
        self.login(self.cajero)

        for cantidad in (0, -5):
            response = self.client.post(
                self.url, {"product": self.cerveza.id, "quantity": cantidad}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(Stock.objects.exists())

    def test_no_se_aceptan_fracciones(self):
        """El inventario se maneja en unidades enteras."""
        self.login(self.cajero)

        response = self.client.post(
            self.url, {"product": self.cerveza.id, "quantity": 2.5}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_se_registran_productos_activos(self):
        """Un producto inactivo no admite entradas de mercancía."""
        inactivo = Product.objects.create(
            name="Cerveza descontinuada", product_type="Bebida", category="Cerveza",
            purchase_price=3000, sale_price=8000, is_active=False,
        )
        self.login(self.cajero)

        response = self.client.post(
            self.url, {"product": inactivo.id, "quantity": 10}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_entrada_genera_un_movimiento_de_inventario(self):
        """Queda trazabilidad del movimiento con su responsable."""
        self.login(self.cajero)
        self.client.post(self.url, {"product": self.cerveza.id, "quantity": 24}, format="json")

        movimiento = StockMovement.objects.get()
        self.assertEqual(movimiento.movement_type, MovementType.ENTRY)
        self.assertEqual(movimiento.quantity, 24)
        self.assertEqual(movimiento.venue, self.galeria)
        self.assertEqual(movimiento.performed_by, self.cajero)

    def test_la_entrada_queda_en_el_log_de_auditoria(self):
        """El log registra producto, cantidad, cajero, sede, fecha y hora."""
        self.login(self.cajero)
        self.client.post(self.url, {"product": self.cerveza.id, "quantity": 24}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.STOCK_ENTRY).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.cajero)
        self.assertIn("24", evento.description)
        self.assertIn("Cerveza Club Colombia", evento.description)
        self.assertIn("Galería", evento.description)
        self.assertIsNotNone(evento.created_at)

    def test_el_stock_actualizado_se_devuelve_de_inmediato(self):
        """El stock resultante es visible al instante."""
        self.login(self.cajero)

        response = self.client.post(
            self.url, {"product": self.cerveza.id, "quantity": 24}, format="json"
        )

        self.assertEqual(response.data["quantity"], 24)
        self.assertEqual(response.data["product_name"], "Cerveza Club Colombia")
        self.assertEqual(response.data["venue_name"], "Galería")
