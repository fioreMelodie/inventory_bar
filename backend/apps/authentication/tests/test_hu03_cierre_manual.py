"""
Pruebas de la HU03 - Cierre de Sesión Manual y Manejo de Pérdida de Conexión.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.authentication.models import UserSession


class LogoutTests(APITestCase):
    """Validación de los criterios de aceptación de la HU03."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.user = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        response = self.client.post(
            reverse("authentication:login"),
            {"username": "admin1", "password": self.password},
            format="json",
        )
        self.access = response.data["access"]
        self.refresh = response.data["refresh"]
        self.session = UserSession.objects.get(id=response.data["session_id"])
        self.url = reverse("authentication:logout")

    def test_cierre_manual_invalida_la_sesion(self):
        """Al cerrar sesión manualmente la sesión queda invalidada."""
        response = self.client.post(
            self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        self.assertEqual(self.session.closing_reason, UserSession.ClosingReason.MANUAL)

    def test_cierre_manual_registra_su_propio_evento(self):
        """La auditoría distingue el cierre manual."""
        self.client.post(self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json")

        self.assertTrue(
            AuditEvent.objects.filter(event_type=EventType.SESSION_LOGOUT).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(event_type=EventType.SESSION_DISCONNECTED).exists()
        )

    def test_cierre_por_desconexion_registra_un_evento_distinto(self):
        """La auditoría distingue el cierre por pérdida de conexión."""
        self.client.post(
            self.url, {"refresh": self.refresh, "reason": "DISCONNECTION"}, format="json"
        )

        self.session.refresh_from_db()
        self.assertEqual(
            self.session.closing_reason, UserSession.ClosingReason.DISCONNECTION
        )
        evento = AuditEvent.objects.filter(
            event_type=EventType.SESSION_DISCONNECTED
        ).first()
        self.assertIsNotNone(evento)
        self.assertIn("conexión", evento.description.lower())

    def test_el_motivo_por_defecto_es_el_cierre_manual(self):
        """Si no se indica motivo, se asume cierre manual."""
        self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.session.refresh_from_db()
        self.assertEqual(self.session.closing_reason, UserSession.ClosingReason.MANUAL)

    def test_el_token_deja_de_servir_tras_cerrar_sesion(self):
        """La sesión cerrada no permite seguir operando."""
        self.client.post(self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

        response = self.client.get(reverse("authentication:current-user"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_cierre_no_elimina_el_historial_del_usuario(self):
        """Cerrar sesión no borra datos: el registro de la sesión se conserva."""
        self.client.post(self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json")

        self.assertTrue(UserSession.objects.filter(id=self.session.id).exists())
        self.assertTrue(AuditEvent.objects.filter(user=self.user).exists())

    def test_no_se_acepta_un_motivo_de_cierre_invalido(self):
        """Solo se admiten los motivos definidos para esta historia."""
        response = self.client.post(
            self.url, {"refresh": self.refresh, "reason": "INACTIVITY"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cerrar_una_sesion_ya_cerrada_es_idempotente(self):
        """Reintentar el cierre no produce error ni cambia el motivo original."""
        self.client.post(self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json")

        response = self.client.post(
            self.url, {"refresh": self.refresh, "reason": "MANUAL"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AuditEvent.objects.filter(event_type=EventType.SESSION_LOGOUT).count(), 1
        )
