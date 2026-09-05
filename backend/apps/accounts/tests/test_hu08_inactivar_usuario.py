"""
Pruebas de la HU08 - Inactivar Usuario.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.authentication.models import UserSession
from apps.locations.models import Venue


class DeactivateUserTests(APITestCase):
    """Validación de los criterios de aceptación de la HU08."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.cajero = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.venue,
        )
        self.url = reverse("accounts:user-deactivate", args=[self.cajero.id])
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def test_la_inactivacion_marca_la_cuenta_como_inactiva(self):
        """El sistema cambia el campo activo a 0."""
        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cajero.refresh_from_db()
        self.assertFalse(self.cajero.is_active)

    def test_la_inactivacion_requiere_confirmacion_explicita(self):
        """Sin confirmación la cuenta permanece activa."""
        response = self.client.post(self.url, {"confirm": False}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)

    def test_un_usuario_inactivo_no_puede_autenticarse(self):
        """La cuenta inactiva queda sin acceso al sistema."""
        self.client.post(self.url, {"confirm": True}, format="json")
        self.client.credentials()

        response = self.client.post(
            reverse("authentication:login"),
            {"username": "cajero1", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_la_sesion_activa_se_invalida_de_inmediato(self):
        """Si el usuario tiene sesión abierta, esta se cierra al instante."""
        self.client.credentials()
        datos_sesion = self.login(self.cajero)
        sesion = UserSession.objects.get(id=datos_sesion["session_id"])
        access_cajero = datos_sesion["access"]

        self.login(self.admin)
        self.client.post(self.url, {"confirm": True}, format="json")

        sesion.refresh_from_db()
        self.assertFalse(sesion.is_active)
        self.assertEqual(
            sesion.closing_reason, UserSession.ClosingReason.USER_DEACTIVATED
        )

        # El token que tenía en la mano deja de servir.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_cajero}")
        response = self.client.get(reverse("authentication:current-user"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_historial_del_usuario_permanece_integro(self):
        """La cuenta no se elimina: su historial de actividad se conserva."""
        self.client.credentials()
        self.login(self.cajero)
        eventos_previos = AuditEvent.objects.filter(user=self.cajero).count()

        self.login(self.admin)
        self.client.post(self.url, {"confirm": True}, format="json")

        self.assertTrue(User.objects.filter(id=self.cajero.id).exists())
        self.assertGreaterEqual(
            AuditEvent.objects.filter(user=self.cajero).count(), eventos_previos
        )

    def test_la_inactivacion_queda_en_el_log_de_auditoria(self):
        """Se genera log de auditoría con la inactivación."""
        self.client.post(self.url, {"confirm": True}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.USER_DEACTIVATED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.admin)
        self.assertIn("cajero1", evento.description)

    def test_un_usuario_inactivo_puede_ser_reactivado(self):
        """El Administrador puede reactivar la cuenta."""
        self.client.post(self.url, {"confirm": True}, format="json")

        response = self.client.post(
            reverse("accounts:user-activate", args=[self.cajero.id]),
            {"confirm": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cajero.refresh_from_db()
        self.assertTrue(self.cajero.is_active)
        self.assertTrue(
            AuditEvent.objects.filter(event_type=EventType.USER_REACTIVATED).exists()
        )

    def test_la_cuenta_reactivada_puede_volver_a_iniciar_sesion(self):
        """Tras la reactivación el usuario recupera el acceso."""
        self.client.post(self.url, {"confirm": True}, format="json")
        self.client.post(
            reverse("accounts:user-activate", args=[self.cajero.id]),
            {"confirm": True},
            format="json",
        )
        self.client.credentials()

        response = self.client.post(
            reverse("authentication:login"),
            {"username": "cajero1", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_no_se_inactiva_dos_veces_la_misma_cuenta(self):
        """Inactivar una cuenta ya inactiva es un error de operación."""
        self.client.post(self.url, {"confirm": True}, format="json")

        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_administrador_no_puede_inactivarse_a_si_mismo(self):
        """Evita que el sistema quede sin administrador operativo."""
        url = reverse("accounts:user-deactivate", args=[self.admin.id])

        response = self.client.post(url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_un_mesero_no_puede_inactivar_cuentas(self):
        """La operación es exclusiva del Administrador."""
        mesero = User.objects.create_user(
            username="mesero1",
            password=self.password,
            full_name="Juan Pérez",
            role=Role.WAITER,
            venue=self.venue,
        )
        self.login(mesero)

        response = self.client.post(self.url, {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_las_cuentas_inactivas_se_consultan_explicitamente(self):
        """El listado por defecto muestra solo cuentas activas."""
        self.client.post(self.url, {"confirm": True}, format="json")
        url = reverse("accounts:user-list")

        activos = [item["username"] for item in self.client.get(url).data["results"]]
        todos = [
            item["username"]
            for item in self.client.get(url, {"include_inactive": "true"}).data["results"]
        ]

        self.assertNotIn("cajero1", activos)
        self.assertIn("cajero1", todos)
