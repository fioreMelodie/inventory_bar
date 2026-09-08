"""
Pruebas de la HU09 - Crear Producto en el Catálogo.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.locations.models import Venue


class CreateProductTests(APITestCase):
    """Validación de los criterios de aceptación de la HU09."""

    def setUp(self):
        self.url = reverse("catalog:product-list")
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def payload(self, **overrides):
        data = {
            "name": "Cerveza Club Colombia",
            "product_type": "Bebida",
            "category": "Cerveza",
            "purchase_price": 3500,
            "sale_price": 9000,
        }
        data.update(overrides)
        return data

    def test_el_administrador_crea_un_producto(self):
        """El producto queda activo y disponible en todas las sedes."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product = Product.objects.get(id=response.data["id"])
        self.assertEqual(product.name, "Cerveza Club Colombia")
        self.assertEqual(product.purchase_price, 3500)
        self.assertEqual(product.sale_price, 9000)
        self.assertTrue(product.is_active)

    def test_el_nombre_del_producto_debe_ser_unico(self):
        """No pueden existir dos productos con el mismo nombre."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Product.objects.count(), 1)

    def test_la_unicidad_del_nombre_ignora_mayusculas(self):
        """'cerveza club colombia' y 'Cerveza Club Colombia' son el mismo producto."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(
            self.url, self.payload(name="cerveza club colombia"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_valor_de_compra_es_obligatorio(self):
        """Sin valor de compra no se puede crear el producto."""
        data = self.payload()
        del data["purchase_price"]

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase_price", response.data)

    def test_el_valor_de_venta_es_obligatorio(self):
        """Sin valor de venta no se puede crear el producto."""
        data = self.payload()
        del data["sale_price"]

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sale_price", response.data)

    def test_los_valores_deben_ser_positivos(self):
        """No se aceptan precios en cero ni negativos."""
        for campo in ("purchase_price", "sale_price"):
            response = self.client.post(self.url, self.payload(**{campo: 0}), format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            response = self.client.post(self.url, self.payload(**{campo: -100}), format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(Product.objects.exists())

    def test_los_valores_deben_ser_numeros_enteros(self):
        """No se admiten fracciones en los precios."""
        response = self.client.post(self.url, self.payload(sale_price=9000.75), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_la_imagen_es_opcional(self):
        """Si no se sube imagen, el producto se crea igual."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(Product.objects.get(id=response.data["id"]).image)

    def test_solo_el_administrador_puede_crear_productos(self):
        """Cajero y Mesero no parametrizan el catálogo."""
        for role, username in ((Role.CASHIER, "cajero1"), (Role.WAITER, "mesero1")):
            user = User.objects.create_user(
                username=username,
                password=self.password,
                full_name="Usuario de prueba",
                role=role,
                venue=self.venue,
            )
            self.login(user)

            response = self.client.post(self.url, self.payload(), format="json")

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Product.objects.exists())

    def test_el_producto_queda_disponible_en_todas_las_sedes(self):
        """El catálogo es global: no se asocia a ninguna sede."""
        Venue.objects.create(name="Zona T")
        response = self.client.post(self.url, self.payload(), format="json")
        product = Product.objects.get(id=response.data["id"])

        # El modelo no tiene relación con sede alguna: es compartido.
        self.assertFalse(
            any(field.name == "venue" for field in Product._meta.get_fields())
        )
        self.assertTrue(product.is_active)

    def test_la_creacion_queda_en_el_log_de_auditoria(self):
        """Se genera log de auditoría de la creación."""
        self.client.post(self.url, self.payload(), format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.PRODUCT_CREATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertIn("Cerveza Club Colombia", evento.description)
