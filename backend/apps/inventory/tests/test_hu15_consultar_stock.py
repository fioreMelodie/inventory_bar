"""
Pruebas de la HU15 - Consultar Stock Disponible por Sede.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue


class VenueStockQueryTests(APITestCase):
    """Validación de los criterios de aceptación de la HU15."""

    def setUp(self):
        self.url = reverse("inventory:venue-stock")
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
        self.aguardiente = Product.objects.create(
            name="Aguardiente Antioqueño", product_type="Bebida",
            category="Licor", purchase_price=28000, sale_price=65000,
        )

        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)
        Stock.objects.create(venue=self.zona_t, product=self.cerveza, quantity=5)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def row(self, response, product_name):
        return next(
            item for item in response.data["results"] if item["product_name"] == product_name
        )

    def test_el_cajero_consulta_el_stock_de_su_sede(self):
        """El Cajero ve las existencias de su sede asignada."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["venue_name"], "Galería")
        self.assertEqual(self.row(response, "Cerveza Club Colombia")["quantity"], 24)

    def test_el_cajero_no_puede_consultar_otra_sede(self):
        """Aunque pida otra sede, solo ve el inventario de la suya."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertEqual(response.data["venue_name"], "Galería")
        self.assertEqual(self.row(response, "Cerveza Club Colombia")["quantity"], 24)

    def test_el_administrador_cambia_de_sede(self):
        """El Administrador ve el stock de todas las sedes."""
        self.login(self.admin)

        galeria = self.client.get(self.url, {"venue": self.galeria.id})
        zona_t = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertEqual(self.row(galeria, "Cerveza Club Colombia")["quantity"], 24)
        self.assertEqual(self.row(zona_t, "Cerveza Club Colombia")["quantity"], 5)

    def test_los_productos_sin_movimientos_aparecen_en_cero(self):
        """Un producto sin entradas se informa con stock cero, no se omite."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        fila = self.row(response, "Aguardiente Antioqueño")
        self.assertEqual(fila["quantity"], 0)

    def test_los_productos_agotados_se_marcan(self):
        """Los productos con stock cero se pueden resaltar en la interfaz."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertTrue(self.row(response, "Aguardiente Antioqueño")["is_out_of_stock"])
        self.assertFalse(self.row(response, "Cerveza Club Colombia")["is_out_of_stock"])

    def test_el_stock_se_muestra_en_unidades_enteras(self):
        """Las cantidades son siempre enteras."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        for item in response.data["results"]:
            self.assertIsInstance(item["quantity"], int)

    def test_filtro_por_nombre_de_producto(self):
        """La búsqueda por nombre acota el listado."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"search": "cerveza"})

        nombres = [item["product_name"] for item in response.data["results"]]
        self.assertEqual(nombres, ["Cerveza Club Colombia"])

    def test_filtro_por_categoria(self):
        """El filtro por categoría acota el listado."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"category": "Licor"})

        nombres = [item["product_name"] for item in response.data["results"]]
        self.assertEqual(nombres, ["Aguardiente Antioqueño"])

    def test_los_productos_inactivos_no_aparecen(self):
        """El listado se construye sobre el catálogo activo."""
        Product.objects.create(
            name="Cerveza descontinuada", product_type="Bebida", category="Cerveza",
            purchase_price=3000, sale_price=8000, is_active=False,
        )
        self.login(self.cajero)

        response = self.client.get(self.url)

        nombres = [item["product_name"] for item in response.data["results"]]
        self.assertNotIn("Cerveza descontinuada", nombres)

    def test_el_mesero_no_accede_al_inventario(self):
        """La consulta de stock es de Cajero y Administrador."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_consulta_refleja_las_entradas_de_inmediato(self):
        """El stock consultado es el actual, sin pasos intermedios."""
        self.login(self.cajero)
        self.client.post(
            reverse("inventory:stock-entry"),
            {"product": self.aguardiente.id, "quantity": 6},
            format="json",
        )

        response = self.client.get(self.url)

        self.assertEqual(self.row(response, "Aguardiente Antioqueño")["quantity"], 6)

    def test_una_sede_inexistente_devuelve_error(self):
        """Pedir una sede que no existe no devuelve datos de otra."""
        self.login(self.admin)

        response = self.client.get(self.url, {"venue": 9999})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
