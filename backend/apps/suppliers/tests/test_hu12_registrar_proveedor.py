"""
Pruebas de la HU12 - Registrar Proveedor.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations.models import Venue
from apps.suppliers.models import Supplier


class RegisterSupplierTests(APITestCase):
    """Validación de los criterios de aceptación de la HU12."""

    def setUp(self):
        self.url = reverse("suppliers:supplier-list")
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
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
            "name": "Distribuidora Bavaria",
            "phone": "601 555 1234",
            "email": "contacto@bavaria.com.co",
        }
        data.update(overrides)
        return data

    def test_el_administrador_registra_un_proveedor(self):
        """El proveedor queda disponible para asociarse a productos."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        supplier = Supplier.objects.get(id=response.data["id"])
        self.assertEqual(supplier.name, "Distribuidora Bavaria")
        self.assertEqual(supplier.phone, "601 555 1234")

    def test_el_nombre_es_obligatorio(self):
        """Sin nombre no se puede registrar el proveedor."""
        response = self.client.post(self.url, {"phone": "601 555 1234"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_el_nombre_debe_ser_unico(self):
        """No se admite un proveedor duplicado."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_la_unicidad_del_nombre_ignora_mayusculas(self):
        """'distribuidora bavaria' y 'Distribuidora Bavaria' son el mismo proveedor."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(
            self.url, self.payload(name="distribuidora bavaria"), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_telefono_y_correo_son_opcionales(self):
        """Solo el nombre es obligatorio."""
        response = self.client.post(self.url, {"name": "Licores del Valle"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        supplier = Supplier.objects.get(name="Licores del Valle")
        self.assertEqual(supplier.phone, "")
        self.assertEqual(supplier.email, "")

    def test_se_valida_el_formato_del_correo(self):
        """Un correo mal formado se rechaza."""
        response = self.client.post(self.url, self.payload(email="no-es-un-correo"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_el_administrador_puede_editar_un_proveedor(self):
        """Los datos de contacto se mantienen actualizados."""
        creado = self.client.post(self.url, self.payload(), format="json")
        detalle = reverse("suppliers:supplier-detail", args=[creado.data["id"]])

        response = self.client.patch(detalle, {"phone": "601 555 9999"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Supplier.objects.get(id=creado.data["id"]).phone, "601 555 9999")

    def test_el_administrador_puede_eliminar_un_proveedor(self):
        """El módulo permite retirar proveedores del directorio."""
        creado = self.client.post(self.url, self.payload(), format="json")
        detalle = reverse("suppliers:supplier-detail", args=[creado.data["id"]])

        response = self.client.delete(detalle)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Supplier.objects.exists())

    def test_la_eliminacion_queda_registrada_en_auditoria(self):
        """El registro de auditoría sobrevive a la eliminación del proveedor."""
        creado = self.client.post(self.url, self.payload(), format="json")
        self.client.delete(reverse("suppliers:supplier-detail", args=[creado.data["id"]]))

        evento = AuditEvent.objects.filter(event_type=EventType.SUPPLIER_DELETED).first()
        self.assertIsNotNone(evento)
        self.assertIn("Distribuidora Bavaria", evento.description)

    def test_solo_el_administrador_gestiona_proveedores(self):
        """Cajero y Mesero no acceden al módulo."""
        for role, username in ((Role.CASHIER, "cajero1"), (Role.WAITER, "mesero1")):
            user = User.objects.create_user(
                username=username, password=self.password,
                full_name="Usuario de prueba", role=role, venue=self.venue,
            )
            self.login(user)

            creacion = self.client.post(self.url, self.payload(), format="json")
            consulta = self.client.get(self.url)

            self.assertEqual(creacion.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(consulta.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_registro_queda_en_el_log_de_auditoria(self):
        """Se genera log de auditoría del registro."""
        self.client.post(self.url, self.payload(), format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.SUPPLIER_CREATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertIn("Distribuidora Bavaria", evento.description)

    def test_el_modulo_no_afecta_el_inventario(self):
        """Es informativo: el proveedor no genera transacciones."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # El modelo no guarda cantidades ni se relaciona con sede o stock.
        campos = {field.name for field in Supplier._meta.get_fields()}
        self.assertNotIn("venue", campos)
        self.assertNotIn("quantity", campos)
