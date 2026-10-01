"""
Pruebas de la renovación del access token.

Corrigen un defecto de la HU02: el access token vencía a los 3 minutos aunque
el usuario estuviera trabajando de forma continua, lo que contradice el
criterio de que cualquier interacción reinicia el contador de inactividad.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.authentication.models import UserSession
from apps.locations.models import Venue


class TokenRefreshTests(APITestCase):
    """La sesión se mantiene mientras haya actividad real."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.venue = Venue.objects.create(name="Galería")
        self.user = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.venue,
        )
        self.url = reverse("authentication:token-refresh")

        response = self.client.post(
            reverse("authentication:login"),
            {"username": "cajero1", "password": self.password},
            format="json",
        )
        self.refresh = response.data["refresh"]
        self.session = UserSession.objects.get(id=response.data["session_id"])

    def simulate_inactivity(self, minutes):
        UserSession.objects.filter(id=self.session.id).update(
            last_activity_at=timezone.now() - timedelta(minutes=minutes)
        )

    def test_se_renueva_el_token_de_una_sesion_activa(self):
        """Un usuario que sigue trabajando obtiene un token nuevo."""
        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_el_token_renovado_sirve_para_operar(self):
        """El access token nuevo es aceptado por la API."""
        nuevo = self.client.post(
            self.url, {"refresh": self.refresh}, format="json"
        ).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {nuevo}")

        response = self.client.get(reverse("authentication:current-user"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "cajero1")

    def test_la_renovacion_cuenta_como_actividad(self):
        """La última actividad de la sesión se actualiza."""
        self.simulate_inactivity(minutes=2)

        self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.session.refresh_from_db()
        self.assertLess(
            timezone.now() - self.session.last_activity_at, timedelta(seconds=10)
        )

    def test_no_se_renueva_una_sesion_inactiva(self):
        """Tras 3 minutos sin actividad la sesión no puede renovarse."""
        self.simulate_inactivity(minutes=4)

        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        self.assertEqual(
            self.session.closing_reason, UserSession.ClosingReason.INACTIVITY
        )

    def test_no_se_renueva_una_sesion_cerrada_manualmente(self):
        """Tras cerrar sesión el refresh token deja de servir."""
        self.client.post(
            reverse("authentication:logout"),
            {"refresh": self.refresh, "reason": "MANUAL"},
            format="json",
        )

        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_se_renueva_la_sesion_de_un_usuario_inactivado(self):
        """Una cuenta inactivada no puede seguir renovando su acceso."""
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(self.url, {"refresh": self.refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)

    def test_un_refresh_token_invalido_se_rechaza(self):
        """Un token manipulado no concede acceso."""
        response = self.client.post(self.url, {"refresh": "token-falso"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_el_refresh_token_rota_en_cada_renovacion(self):
        """Se entrega un refresh token nuevo y el anterior queda revocado."""
        primera = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        nuevo_refresh = primera.data["refresh"]

        self.assertNotEqual(nuevo_refresh, self.refresh)

        reutilizado = self.client.post(self.url, {"refresh": self.refresh}, format="json")
        self.assertEqual(reutilizado.status_code, status.HTTP_401_UNAUTHORIZED)

        vigente = self.client.post(self.url, {"refresh": nuevo_refresh}, format="json")
        self.assertEqual(vigente.status_code, status.HTTP_200_OK)

    def test_la_sesion_sobrevive_mas_alla_de_la_vida_del_access_token(self):
        """
        Escenario del defecto: un usuario trabaja durante más tiempo del que
        dura el access token, renovando cada vez que interactúa.
        """
        for _ in range(5):
            self.simulate_inactivity(minutes=2)
            respuesta = self.client.post(
                self.url, {"refresh": self.refresh}, format="json"
            )
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
            self.refresh = respuesta.data["refresh"]

        self.session.refresh_from_db()
        self.assertTrue(self.session.is_active)
