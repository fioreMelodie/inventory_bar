"""
Pruebas de la HU04 - Crear Sede.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations.models import Venue


class CreateVenueTests(APITestCase):
    """Validación de los criterios de aceptación de la HU04."""

    def setUp(self):
        self.url = reverse("locations:venue-list")
        self.password = "Cafe2026*Bar"
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_administrador_crea_una_sede(self):
        """La sede se crea con estado activo."""
        self.login(self.admin)

        response = self.client.post(
            self.url, {"name": "Zona T", "address": "Calle 85 #12-34"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        venue = Venue.objects.get(id=response.data["id"])
        self.assertEqual(venue.name, "Zona T")
        self.assertEqual(venue.address, "Calle 85 #12-34")
        self.assertTrue(venue.is_active)

    def test_la_direccion_es_opcional(self):
        """El campo nombre es obligatorio; dirección es opcional."""
        self.login(self.admin)

        response = self.client.post(self.url, {"name": "Modelia"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Venue.objects.get(name="Modelia").address, "")

    def test_el_nombre_es_obligatorio(self):
        """Sin nombre no se puede crear la sede."""
        self.login(self.admin)

        response = self.client.post(self.url, {"address": "Calle 85"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_no_se_permiten_dos_sedes_con_el_mismo_nombre(self):
        """No se pueden crear dos sedes con el mismo nombre."""
        Venue.objects.create(name="Galería")
        self.login(self.admin)

        response = self.client.post(self.url, {"name": "Galería"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Venue.objects.filter(name="Galería").count(), 1)

    def test_la_validacion_de_nombre_duplicado_ignora_mayusculas(self):
        """'galería' y 'Galería' son la misma sede."""
        Venue.objects.create(name="Galería")
        self.login(self.admin)

        response = self.client.post(self.url, {"name": "galería"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_el_administrador_puede_crear_sedes(self):
        """Cajero y Mesero no pueden crear sedes."""
        for role, username in ((Role.CASHIER, "cajero1"), (Role.WAITER, "mesero1")):
            user = User.objects.create_user(
                username=username,
                password=self.password,
                full_name="Usuario de prueba",
                role=role,
            )
            self.login(user)

            response = self.client.post(self.url, {"name": f"Sede {username}"}, format="json")

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Venue.objects.exists())

    def test_un_usuario_sin_sesion_no_puede_crear_sedes(self):
        """El endpoint exige autenticación."""
        response = self.client.post(self.url, {"name": "Suba"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_la_creacion_queda_en_el_log_de_auditoria(self):
        """Se registra la creación con fecha, hora y usuario."""
        self.login(self.admin)
        self.client.post(self.url, {"name": "Zona T"}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.VENUE_CREATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertEqual(evento.entity, "Venue")
        self.assertIn("Zona T", evento.description)

    def test_la_sede_creada_queda_disponible_de_inmediato(self):
        """La sede aparece enseguida en el listado usado por los filtros."""
        self.login(self.admin)
        self.client.post(self.url, {"name": "Zona T"}, format="json")

        response = self.client.get(self.url)

        nombres = [item["name"] for item in response.data["results"]]
        self.assertIn("Zona T", nombres)

    def test_la_sesion_registra_la_sede_asignada(self):
        """Criterio de la HU01: la sesión registra la sede del usuario."""
        venue = Venue.objects.create(name="Galería")
        cajero = User.objects.create_user(
            username="cajero2",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=venue,
        )

        response = self.client.post(
            reverse("authentication:login"),
            {"username": cajero.username, "password": self.password},
            format="json",
        )

        self.assertEqual(response.data["user"]["venue_name"], "Galería")
