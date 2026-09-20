"""
Pruebas de la HU11 - Consultar Catálogo de Productos.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue


class ProductCatalogQueryTests(APITestCase):
    """Validación de los criterios de aceptación de la HU11."""

    def setUp(self):
        self.url = reverse("catalog:product-list")
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")

        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )
        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.venue,
        )
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.venue,
        )

        Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        Product.objects.create(
            name="Aguardiente Antioqueño", product_type="Bebida",
            category="Licor", purchase_price=28000, sale_price=65000,
        )
        Product.objects.create(
            name="Maní salado", product_type="Comida",
            category="Pasaboca", purchase_price=1200, sale_price=4000,
        )
        self.inactivo = Product.objects.create(
            name="Cerveza descontinuada", product_type="Bebida",
            category="Cerveza", purchase_price=3000, sale_price=8000,
            is_active=False,
        )

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def names(self, response):
        return [item["name"] for item in response.data["results"]]

    def test_los_tres_roles_pueden_consultar_el_catalogo(self):
        """Administrador, Cajero y Mesero acceden a la consulta."""
        for user in (self.admin, self.cajero, self.mesero):
            self.login(user)

            response = self.client.get(self.url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data["results"]), 3)

    def test_solo_se_muestran_productos_activos(self):
        """Los productos con activo=0 no aparecen."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertNotIn("Cerveza descontinuada", self.names(response))

    def test_el_administrador_ve_el_valor_de_compra(self):
        """El valor de compra es visible para el Administrador."""
        self.login(self.admin)

        response = self.client.get(self.url)

        self.assertIn("purchase_price", response.data["results"][0])

    def test_el_cajero_y_el_mesero_no_ven_el_valor_de_compra(self):
        """El valor de compra es visible únicamente para el Administrador."""
        for user in (self.cajero, self.mesero):
            self.login(user)

            response = self.client.get(self.url)

            for item in response.data["results"]:
                self.assertNotIn("purchase_price", item)
                self.assertIn("sale_price", item)

    def test_el_catalogo_es_de_solo_lectura_para_cajero_y_mesero(self):
        """Ninguno de los dos roles puede crear ni modificar productos."""
        producto = Product.objects.get(name="Maní salado")
        detalle = reverse("catalog:product-detail", args=[producto.id])

        for user in (self.cajero, self.mesero):
            self.login(user)

            creacion = self.client.post(
                self.url,
                {"name": "Nuevo", "product_type": "Bebida", "category": "Cerveza",
                 "purchase_price": 1000, "sale_price": 2000},
                format="json",
            )
            edicion = self.client.patch(detalle, {"sale_price": 1}, format="json")

            self.assertEqual(creacion.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(edicion.status_code, status.HTTP_403_FORBIDDEN)

    def test_filtro_por_tipo(self):
        """El filtro por tipo devuelve solo los productos de ese tipo."""
        self.login(self.mesero)

        response = self.client.get(self.url, {"type": "Comida"})

        self.assertEqual(self.names(response), ["Maní salado"])

    def test_filtro_por_categoria(self):
        """El filtro por categoría acota el listado."""
        self.login(self.mesero)

        response = self.client.get(self.url, {"category": "Licor"})

        self.assertEqual(self.names(response), ["Aguardiente Antioqueño"])

    def test_los_filtros_se_combinan(self):
        """Tipo y categoría pueden aplicarse a la vez."""
        self.login(self.admin)

        response = self.client.get(self.url, {"type": "Bebida", "category": "Cerveza"})

        self.assertEqual(self.names(response), ["Cerveza Club Colombia"])

    def test_busqueda_por_nombre(self):
        """La búsqueda por nombre es parcial y sin distinguir mayúsculas."""
        self.login(self.mesero)

        response = self.client.get(self.url, {"search": "aguardiente"})

        self.assertEqual(self.names(response), ["Aguardiente Antioqueño"])

    def test_el_filtro_de_inactivos_es_exclusivo_del_administrador(self):
        """Un Mesero no puede ver productos inactivos ni forzando el parámetro."""
        self.login(self.mesero)

        response = self.client.get(self.url, {"include_inactive": "true"})

        self.assertNotIn("Cerveza descontinuada", self.names(response))

    def test_la_respuesta_incluye_la_imagen_cuando_existe(self):
        """La visualización incluye imagen si está disponible."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        for item in response.data["results"]:
            self.assertIn("image", item)

    def test_la_consulta_exige_autenticacion(self):
        """El catálogo no es público."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
