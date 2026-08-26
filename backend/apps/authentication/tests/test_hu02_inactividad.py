"""
Pruebas de la HU02 - Cierre Automático de Sesión por Inactividad.

Verifican que la invalidación ocurre en servidor y no solo en el frontend.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.authentication.authentication import INACTIVITY_TIMEOUT
from apps.authentication.models import UserSession


class InactivityTimeoutTests(APITestCase):
    """Validación de los criterios de aceptación de la HU02."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.user = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
        )
        response = self.client.post(
            reverse("authentication:login"),
            {"username": "cajero1", "password": self.password},
            format="json",
        )
        self.access = response.data["access"]
        self.refresh = response.data["refresh"]
        self.session = UserSession.objects.get(id=response.data["session_id"])

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def simulate_inactivity(self, minutes):
        """Retrocede la última actividad registrada para simular el paso del tiempo."""
        UserSession.objects.filter(id=self.session.id).update(
            last_activity_at=timezone.now() - timedelta(minutes=minutes)
        )

    def test_el_tiempo_de_inactividad_es_de_tres_minutos(self):
        """El tiempo de inactividad es exactamente 3 minutos."""
        self.assertEqual(INACTIVITY_TIMEOUT, timedelta(minutes=3))

    def test_sesion_activa_permite_operar(self):
        """Antes de cumplirse el tiempo, la sesión sigue siendo válida."""
        self.authenticate()
        self.simulate_inactivity(minutes=2)

        response = self.client.get(reverse("authentication:current-user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cada_interaccion_reinicia_el_contador(self):
        """Cualquier petición del usuario actualiza la última actividad."""
        self.authenticate()
        self.simulate_inactivity(minutes=2)

        self.client.get(reverse("authentication:current-user"))

        self.session.refresh_from_db()
        self.assertLess(
            timezone.now() - self.session.last_activity_at, timedelta(seconds=10)
        )

    def test_el_servidor_invalida_la_sesion_tras_tres_minutos(self):
        """La sesión se invalida en servidor, no solo en el frontend."""
        self.authenticate()
        self.simulate_inactivity(minutes=4)

        response = self.client.get(reverse("authentication:current-user"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        self.assertEqual(
            self.session.closing_reason, UserSession.ClosingReason.INACTIVITY
        )

    def test_el_cierre_por_inactividad_queda_en_auditoria(self):
        """El log registra usuario, fecha, hora y causa del cierre."""
        self.authenticate()
        self.simulate_inactivity(minutes=4)
        self.client.get(reverse("authentication:current-user"))

        evento = AuditEvent.objects.filter(event_type=EventType.SESSION_TIMEOUT).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.username, "cajero1")
        self.assertEqual(evento.user, self.user)
        self.assertIn("inactividad", evento.description.lower())
        self.assertIsNotNone(evento.created_at)

    def test_endpoint_de_expiracion_cierra_la_sesion(self):
        """El frontend puede notificar el vencimiento de su temporizador."""
        response = self.client.post(
            reverse("authentication:session-expire"),
            {"refresh": self.refresh},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        self.assertEqual(
            self.session.closing_reason, UserSession.ClosingReason.INACTIVITY
        )

    def test_token_de_una_sesion_cerrada_deja_de_servir(self):
        """Tras cerrarse la sesión, el access token vigente ya no es aceptado."""
        self.client.post(
            reverse("authentication:session-expire"),
            {"refresh": self.refresh},
            format="json",
        )
        self.authenticate()

        response = self.client.get(reverse("authentication:current-user"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expirar_una_sesion_ya_cerrada_no_produce_error(self):
        """Reintentar el cierre es idempotente."""
        url = reverse("authentication:session-expire")
        self.client.post(url, {"refresh": self.refresh}, format="json")

        response = self.client.post(url, {"refresh": self.refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
