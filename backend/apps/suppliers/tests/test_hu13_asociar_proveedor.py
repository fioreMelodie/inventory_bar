"""
Pruebas de la HU13 - Asociar Proveedor a Productos del Catálogo.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.suppliers.models import Supplier


class LinkSupplierProductsTests(APITestCase):
    """Validación de los criterios de aceptación de la HU13."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )

        self.bavaria = Supplier.objects.create(name="Distribuidora Bavaria")
        self.licores = Supplier.objects.create(name="Licores del Valle")

        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        self.aguardiente = Product.objects.create(
            name="Aguardiente Antioqueño", product_type="Bebida",
            category="Licor", purchase_price=28000, sale_price=65000,
        )
        self.mani = Product.objects.create(
            name="Maní salado", product_type="Comida",
            category="Pasaboca", purchase_price=1200, sale_price=4000,
        )

        self.url = reverse("suppliers:supplier-products", args=[self.bavaria.id])
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_se_asocian_varios_productos_a_un_proveedor(self):
        """Un proveedor puede estar asociado a múltiples productos."""
        response = self.client.put(
            self.url,
            {"products": [self.cerveza.id, self.mani.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cerveza.refresh_from_db()
        self.mani.refresh_from_db()
        self.assertEqual(self.cerveza.supplier, self.bavaria)
        self.assertEqual(self.mani.supplier, self.bavaria)

    def test_un_producto_tiene_un_solo_proveedor_principal(self):
        """Asociarlo a otro proveedor lo retira automáticamente del anterior."""
        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        otra_url = reverse("suppliers:supplier-products", args=[self.licores.id])
        self.client.put(otra_url, {"products": [self.cerveza.id]}, format="json")

        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.supplier, self.licores)
        self.assertEqual(self.bavaria.products.count(), 0)

    def test_omitir_un_producto_elimina_su_asociacion(self):
        """El Administrador puede modificar o eliminar la asociación."""
        self.client.put(
            self.url, {"products": [self.cerveza.id, self.mani.id]}, format="json"
        )

        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        self.mani.refresh_from_db()
        self.assertIsNone(self.mani.supplier)
        self.assertEqual(self.bavaria.products.count(), 1)

    def test_se_pueden_desvincular_todos_los_productos(self):
        """Enviar una lista vacía deja al proveedor sin productos."""
        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        response = self.client.put(self.url, {"products": []}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.bavaria.products.count(), 0)

    def test_se_consultan_los_productos_del_proveedor(self):
        """Desde el perfil del proveedor se ven los productos que suministra."""
        self.client.put(
            self.url, {"products": [self.cerveza.id, self.mani.id]}, format="json"
        )

        response = self.client.get(self.url)

        nombres = sorted(item["name"] for item in response.data)
        self.assertEqual(nombres, ["Cerveza Club Colombia", "Maní salado"])

    def test_el_catalogo_muestra_el_proveedor_del_producto(self):
        """La relación se refleja en el catálogo de productos."""
        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        response = self.client.get(reverse("catalog:product-list"))

        producto = next(
            item for item in response.data["results"] if item["id"] == self.cerveza.id
        )
        self.assertEqual(producto["supplier"], self.bavaria.id)
        self.assertEqual(producto["supplier_name"], "Distribuidora Bavaria")

    def test_el_proveedor_informa_cuantos_productos_suministra(self):
        """El directorio muestra el número de productos asociados."""
        self.client.put(
            self.url, {"products": [self.cerveza.id, self.mani.id]}, format="json"
        )

        response = self.client.get(reverse("suppliers:supplier-list"))

        proveedor = next(
            item for item in response.data["results"] if item["id"] == self.bavaria.id
        )
        self.assertEqual(proveedor["product_count"], 2)

    def test_tambien_se_asigna_el_proveedor_desde_el_producto(self):
        """La asociación puede hacerse desde el detalle del producto."""
        url = reverse("catalog:product-detail", args=[self.aguardiente.id])

        response = self.client.patch(url, {"supplier": self.licores.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.aguardiente.refresh_from_db()
        self.assertEqual(self.aguardiente.supplier, self.licores)

    def test_eliminar_el_proveedor_no_elimina_sus_productos(self):
        """La asociación es informativa: el producto sobrevive al proveedor."""
        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        self.client.delete(reverse("suppliers:supplier-detail", args=[self.bavaria.id]))

        self.cerveza.refresh_from_db()
        self.assertTrue(Product.objects.filter(id=self.cerveza.id).exists())
        self.assertIsNone(self.cerveza.supplier)

    def test_la_asociacion_no_genera_ordenes_de_compra(self):
        """El módulo no produce transacciones ni movimientos de inventario."""
        eventos_previos = AuditEvent.objects.count()

        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        # El único efecto es el propio registro de auditoría de la asociación.
        self.assertEqual(AuditEvent.objects.count(), eventos_previos + 1)
        self.assertEqual(
            AuditEvent.objects.first().event_type, EventType.SUPPLIER_PRODUCTS_LINKED
        )

    def test_la_asociacion_queda_en_el_log_de_auditoria(self):
        """Se registra qué se asoció y qué se desvinculó."""
        self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        evento = AuditEvent.objects.filter(
            event_type=EventType.SUPPLIER_PRODUCTS_LINKED
        ).first()
        self.assertIsNotNone(evento)
        self.assertIn("Distribuidora Bavaria", evento.description)
        self.assertIn("Asociados: 1", evento.description)

    def test_solo_el_administrador_puede_asociar_productos(self):
        """La operación es exclusiva del Administrador."""
        cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.venue,
        )
        self.login(cajero)

        response = self.client.put(self.url, {"products": [self.cerveza.id]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
