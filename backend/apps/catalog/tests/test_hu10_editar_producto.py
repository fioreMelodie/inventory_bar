"""
Pruebas de la HU10 - Editar Producto del Catálogo.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.locations.models import Venue


class UpdateProductTests(APITestCase):
    """Validación de los criterios de aceptación de la HU10."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.product = Product.objects.create(
            name="Cerveza Club Colombia",
            product_type="Bebida",
            category="Cerveza",
            purchase_price=3500,
            sale_price=9000,
        )
        self.url = reverse("catalog:product-detail", args=[self.product.id])
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_administrador_actualiza_los_atributos(self):
        """Se pueden modificar nombre, tipo, categoría y precios."""
        response = self.client.patch(
            self.url,
            {"name": "Cerveza Club Colombia 330ml", "category": "Cerveza nacional",
             "sale_price": 10000},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Cerveza Club Colombia 330ml")
        self.assertEqual(self.product.category, "Cerveza nacional")
        self.assertEqual(self.product.sale_price, 10000)

    def test_el_nombre_no_puede_coincidir_con_otro_producto(self):
        """Si el nombre se modifica, debe seguir siendo único."""
        Product.objects.create(
            name="Aguardiente Antioqueño",
            product_type="Bebida",
            category="Licor",
            purchase_price=28000,
            sale_price=65000,
        )

        response = self.client.patch(
            self.url, {"name": "Aguardiente Antioqueño"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conservar_el_propio_nombre_no_se_considera_duplicado(self):
        """Editar otros campos sin tocar el nombre no debe fallar."""
        response = self.client.patch(
            self.url,
            {"name": "Cerveza Club Colombia", "sale_price": 9500},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_el_administrador_puede_inactivar_un_producto(self):
        """El producto se retira del catálogo sin eliminarlo."""
        response = self.client.patch(self.url, {"is_active": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
        self.assertTrue(Product.objects.filter(id=self.product.id).exists())

    def test_un_producto_inactivo_no_aparece_en_el_catalogo(self):
        """No debe mostrarse en pedidos ni en el catálogo de meseros."""
        self.client.patch(self.url, {"is_active": False}, format="json")

        mesero = User.objects.create_user(
            username="mesero1",
            password=self.password,
            full_name="Juan Pérez",
            role=Role.WAITER,
            venue=self.venue,
        )
        self.login(mesero)

        response = self.client.get(reverse("catalog:product-list"))

        nombres = [item["name"] for item in response.data["results"]]
        self.assertNotIn("Cerveza Club Colombia", nombres)

    def test_el_administrador_puede_consultar_los_inactivos(self):
        """El histórico del producto permanece accesible."""
        self.client.patch(self.url, {"is_active": False}, format="json")

        response = self.client.get(
            reverse("catalog:product-list"), {"include_inactive": "true"}
        )

        nombres = [item["name"] for item in response.data["results"]]
        self.assertIn("Cerveza Club Colombia", nombres)

    def test_un_producto_inactivo_puede_reactivarse(self):
        """La inactivación es reversible."""
        self.client.patch(self.url, {"is_active": False}, format="json")

        response = self.client.patch(self.url, {"is_active": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_active)

    def test_los_cambios_aplican_en_todas_las_sedes(self):
        """El catálogo es global: no existe precio por sede."""
        Venue.objects.create(name="Zona T")
        self.client.patch(self.url, {"sale_price": 12000}, format="json")

        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_price, 12000)
        # No hay ninguna entidad de precio por sede que pudiera desincronizarse.
        self.assertFalse(
            any(field.name == "venue" for field in Product._meta.get_fields())
        )

    def test_solo_el_administrador_puede_editar_productos(self):
        """El Cajero no parametriza el catálogo."""
        cajero = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.venue,
        )
        self.login(cajero)

        response = self.client.patch(self.url, {"sale_price": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_auditoria_registra_los_campos_modificados(self):
        """Se genera log de auditoría con los campos modificados."""
        self.client.patch(self.url, {"sale_price": 11000}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.PRODUCT_UPDATED).first()
        self.assertIsNotNone(evento)
        self.assertIn("sale_price", evento.description)
        self.assertIn("9000", evento.description)
        self.assertIn("11000", evento.description)

    def test_la_inactivacion_tambien_queda_auditada(self):
        """El cambio de estado se registra como una modificación más."""
        self.client.patch(self.url, {"is_active": False}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.PRODUCT_UPDATED).first()
        self.assertIn("is_active", evento.description)
