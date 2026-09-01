"""
Pruebas de la HU06 - Crear Usuario con Rol y Sede Asignada.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations.models import Venue


class CreateUserTests(APITestCase):
    """Validación de los criterios de aceptación de la HU06."""

    def setUp(self):
        self.url = reverse("accounts:user-list")
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
            "username": "mesero1",
            "full_name": "Juan Pérez",
            "role": Role.WAITER,
            "venue": self.venue.id,
            "password": "Temporal2026*",
        }
        data.update(overrides)
        return data

    def test_el_administrador_crea_una_cuenta_con_rol_y_sede(self):
        """La cuenta queda activa y lista para iniciar sesión."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="mesero1")
        self.assertEqual(user.full_name, "Juan Pérez")
        self.assertEqual(user.role, Role.WAITER)
        self.assertEqual(user.venue, self.venue)
        self.assertTrue(user.is_active)

    def test_la_contrasena_se_almacena_cifrada(self):
        """La contraseña nunca se guarda en texto plano."""
        self.client.post(self.url, self.payload(), format="json")

        user = User.objects.get(username="mesero1")
        self.assertNotEqual(user.password, "Temporal2026*")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertTrue(user.check_password("Temporal2026*"))

    def test_la_cuenta_creada_puede_iniciar_sesion(self):
        """El usuario queda habilitado para autenticarse."""
        self.client.post(self.url, self.payload(), format="json")
        self.client.credentials()

        response = self.client.post(
            reverse("authentication:login"),
            {"username": "mesero1", "password": "Temporal2026*"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["venue_name"], "Galería")

    def test_el_nombre_de_usuario_debe_ser_unico(self):
        """No pueden existir dos cuentas con el mismo nombre de usuario."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(self.url, self.payload(full_name="Otra persona"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(username="mesero1").count(), 1)

    def test_la_unicidad_del_usuario_ignora_mayusculas(self):
        """'Mesero1' y 'mesero1' son la misma cuenta."""
        self.client.post(self.url, self.payload(), format="json")

        response = self.client.post(self.url, self.payload(username="Mesero1"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_cajero_requiere_sede_asignada(self):
        """La sede determina qué información puede ver el Cajero."""
        response = self.client.post(
            self.url,
            self.payload(username="cajero1", role=Role.CASHIER, venue=None),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("venue", response.data)

    def test_el_mesero_requiere_sede_asignada(self):
        """La sede determina qué información puede ver el Mesero."""
        response = self.client.post(self.url, self.payload(venue=None), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("venue", response.data)

    def test_el_administrador_puede_quedar_sin_sede_fija(self):
        """El Administrador accede a todas las sedes."""
        response = self.client.post(
            self.url,
            self.payload(username="admin2", role=Role.ADMIN, venue=None),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(User.objects.get(username="admin2").venue)

    def test_el_administrador_puede_asignarse_a_cualquier_sede(self):
        """Un Administrador puede tener sede asignada si la operación lo requiere."""
        response = self.client.post(
            self.url,
            self.payload(username="admin3", role=Role.ADMIN, venue=self.venue.id),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get(username="admin3").venue, self.venue)

    def test_no_se_puede_asignar_una_sede_inactiva(self):
        """Una sede inactiva no aparece en la selección de sede."""
        inactiva = Venue.objects.create(name="Suba", is_active=False)

        response = self.client.post(self.url, self.payload(venue=inactiva.id), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_se_rechaza_una_contrasena_debil(self):
        """Se aplican las reglas de robustez de contraseña (OWASP)."""
        response = self.client.post(self.url, self.payload(password="12345678"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_no_existe_autoregistro(self):
        """Sin sesión de Administrador no es posible crear cuentas."""
        self.client.credentials()

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(User.objects.filter(username="mesero1").exists())

    def test_un_cajero_no_puede_crear_cuentas(self):
        """Únicamente el Administrador gestiona cuentas."""
        cajero = User.objects.create_user(
            username="cajero9",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.venue,
        )
        self.login(cajero)

        response = self.client.post(self.url, self.payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_la_creacion_queda_en_el_log_de_auditoria(self):
        """Se registra la creación con el rol y la sede asignados."""
        self.client.post(self.url, self.payload(), format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.USER_CREATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertIn("mesero1", evento.description)
        self.assertIn("Mesero", evento.description)
        self.assertIn("Galería", evento.description)

    def test_la_respuesta_no_expone_la_contrasena(self):
        """El campo de contraseña es de solo escritura."""
        response = self.client.post(self.url, self.payload(), format="json")

        self.assertNotIn("password", response.data)
