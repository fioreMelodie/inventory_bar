"""
Pruebas de la HU05 - Editar e Inactivar Sede.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations import services
from apps.locations.models import Venue


class UpdateVenueTests(APITestCase):
    """Edición de los datos de una sede existente."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.venue = Venue.objects.create(name="Zona T", address="Calle 85")
        self.url = reverse("locations:venue-detail", args=[self.venue.id])
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_administrador_actualiza_nombre_y_direccion(self):
        """Los cambios quedan reflejados en el sistema."""
        response = self.client.patch(
            self.url, {"name": "Zona T Norte", "address": "Calle 85 #12-34"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.venue.refresh_from_db()
        self.assertEqual(self.venue.name, "Zona T Norte")
        self.assertEqual(self.venue.address, "Calle 85 #12-34")

    def test_no_se_permite_un_nombre_ya_usado_por_otra_sede(self):
        """Al editar se valida que el nombre siga siendo único."""
        Venue.objects.create(name="Modelia")

        response = self.client.patch(self.url, {"name": "Modelia"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conservar_el_propio_nombre_no_se_considera_duplicado(self):
        """Editar solo la dirección no debe fallar por nombre duplicado."""
        response = self.client.patch(
            self.url, {"name": "Zona T", "address": "Nueva dirección"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_la_edicion_registra_el_valor_anterior_y_el_nuevo(self):
        """La auditoría deja constancia del cambio realizado."""
        self.client.patch(self.url, {"name": "Zona T Norte"}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.VENUE_UPDATED).first()
        self.assertIsNotNone(evento)
        self.assertIn("Zona T", evento.description)
        self.assertIn("Zona T Norte", evento.description)

    def test_solo_el_administrador_puede_editar_sedes(self):
        """Un Cajero no puede modificar la parametrización de sedes."""
        cajero = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.venue,
        )
        self.login(cajero)

        response = self.client.patch(self.url, {"name": "Otra"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeactivateVenueTests(APITestCase):
    """Inactivación de una sede."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.venue = Venue.objects.create(name="Modelia")
        self.url = reverse("locations:venue-deactivate", args=[self.venue.id])
        self.login(self.admin)

    def tearDown(self):
        # Las guardas registradas por una prueba no deben afectar a las demás.
        services._DEACTIVATION_GUARDS.clear()

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_la_inactivacion_cambia_el_estado_de_la_sede(self):
        """La sede queda en estado INACTIVA."""
        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.venue.refresh_from_db()
        self.assertFalse(self.venue.is_active)

    def test_la_inactivacion_requiere_confirmacion_explicita(self):
        """Sin confirmación la sede no se inactiva."""
        response = self.client.post(self.url, {"confirm": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.venue.refresh_from_db()
        self.assertTrue(self.venue.is_active)

    def test_sin_el_campo_de_confirmacion_no_se_inactiva(self):
        """La confirmación es obligatoria."""
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.venue.refresh_from_db()
        self.assertTrue(self.venue.is_active)

    def test_los_usuarios_de_la_sede_quedan_sin_sede_asignada(self):
        """Los usuarios asignados requieren reasignación."""
        cajero = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.venue,
        )

        self.client.post(self.url, {"confirm": True}, format="json")

        cajero.refresh_from_db()
        self.assertIsNone(cajero.venue)

    def test_no_se_inactiva_una_sede_con_operacion_en_curso(self):
        """No se puede inactivar una sede con pedidos abiertos."""
        services.register_deactivation_guard(
            lambda venue: "This venue has tables with open orders."
        )

        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.venue.refresh_from_db()
        self.assertTrue(self.venue.is_active)

    def test_una_sede_inactiva_no_aparece_en_el_listado(self):
        """No debe ofrecerse al crear usuarios o pedidos."""
        self.client.post(self.url, {"confirm": True}, format="json")

        response = self.client.get(reverse("locations:venue-list"))

        nombres = [item["name"] for item in response.data["results"]]
        self.assertNotIn("Modelia", nombres)

    def test_la_sede_inactiva_sigue_siendo_consultable(self):
        """El historial de la sede permanece accesible."""
        self.client.post(self.url, {"confirm": True}, format="json")

        response = self.client.get(
            reverse("locations:venue-list"), {"include_inactive": "true"}
        )

        nombres = [item["name"] for item in response.data["results"]]
        self.assertIn("Modelia", nombres)

    def test_la_inactivacion_queda_en_el_log_de_auditoria(self):
        """Se genera log de auditoría con el cambio realizado."""
        self.client.post(self.url, {"confirm": True}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.VENUE_DEACTIVATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertIn("Modelia", evento.description)

    def test_no_se_inactiva_dos_veces_la_misma_sede(self):
        """Inactivar una sede ya inactiva es un error de operación."""
        self.client.post(self.url, {"confirm": True}, format="json")

        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_el_administrador_puede_inactivar_sedes(self):
        """La operación es exclusiva del Administrador."""
        mesero = User.objects.create_user(
            username="mesero1",
            password=self.password,
            full_name="Juan Pérez",
            role=Role.WAITER,
        )
        self.login(mesero)

        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
