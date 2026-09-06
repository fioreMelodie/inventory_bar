"""
Pruebas de la HU01 - Inicio de Sesión con Credenciales.

Cada prueba verifica un criterio de aceptación del documento de la historia.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.authentication.models import UserSession
from apps.authentication.views import INVALID_CREDENTIALS_MESSAGE


class LoginTests(APITestCase):
    """Validación de los criterios de aceptación de la HU01."""

    def setUp(self):
        self.url = reverse("authentication:login")
        self.password = "Cafe2026*Bar"
        self.user = User.objects.create_user(
            username="mesero1",
            password=self.password,
            full_name="Juan Pérez",
            role=Role.WAITER,
        )

    def login(self, username, password):
        return self.client.post(
            self.url, {"username": username, "password": password}, format="json"
        )

    def test_credenciales_validas_crean_sesion_y_devuelven_tokens(self):
        """Con credenciales válidas se entrega el token y se crea la sesión."""
        response = self.login("mesero1", self.password)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], Role.WAITER)
        self.assertEqual(response.data["user"]["full_name"], "Juan Pérez")

        # La sesión registra usuario, rol y fecha y hora de ingreso.
        session = UserSession.objects.get(id=response.data["session_id"])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.role, Role.WAITER)
        self.assertIsNotNone(session.started_at)
        self.assertTrue(session.is_active)

    def test_login_exitoso_queda_en_el_log_de_auditoria(self):
        """El inicio de sesión se registra en el log de auditoría."""
        self.login("mesero1", self.password)

        evento = AuditEvent.objects.filter(event_type=EventType.LOGIN_SUCCESS).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.username, "mesero1")
        self.assertEqual(evento.user, self.user)

    def test_contrasena_incorrecta_no_revela_cual_campo_fallo(self):
        """El mensaje de error es genérico por seguridad."""
        response = self.login("mesero1", "contrasena-incorrecta")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], INVALID_CREDENTIALS_MESSAGE)

    def test_usuario_inexistente_devuelve_el_mismo_mensaje(self):
        """Un usuario inexistente produce exactamente el mismo error."""
        response = self.login("no-existe", "cualquier-clave")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], INVALID_CREDENTIALS_MESSAGE)

    def test_usuario_inactivo_no_puede_iniciar_sesion(self):
        """Solo los usuarios con estado activo=1 pueden autenticarse."""
        self.user.is_active = False
        self.user.save()

        response = self.login("mesero1", self.password)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], INVALID_CREDENTIALS_MESSAGE)
        self.assertFalse(UserSession.objects.exists())

    def test_intento_fallido_queda_en_el_log_de_auditoria(self):
        """Los intentos fallidos también se registran en auditoría."""
        self.login("mesero1", "clave-mala")

        evento = AuditEvent.objects.filter(event_type=EventType.LOGIN_FAILED).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.username, "mesero1")
        self.assertIn("Contraseña incorrecta", evento.description)

    def test_bloqueo_tras_tres_intentos_fallidos_consecutivos(self):
        """Tras 3 intentos fallidos el acceso se bloquea 5 minutos."""
        for _ in range(3):
            self.login("mesero1", "clave-mala")

        # El cuarto intento se rechaza incluso con la contraseña correcta.
        response = self.login("mesero1", self.password)

        self.assertEqual(response.status_code, status.HTTP_423_LOCKED)
        self.assertTrue(response.data["locked"])
        self.assertGreater(response.data["retry_after_seconds"], 0)
        self.assertIn("locked", response.data["detail"].lower())
        self.assertFalse(UserSession.objects.exists())

    def test_bloqueo_se_registra_en_auditoria(self):
        """El bloqueo genera su propio evento de auditoría."""
        for _ in range(3):
            self.login("mesero1", "clave-mala")
        self.login("mesero1", self.password)

        self.assertTrue(
            AuditEvent.objects.filter(event_type=EventType.LOGIN_BLOCKED).exists()
        )

    def test_dos_intentos_fallidos_no_bloquean_la_cuenta(self):
        """El bloqueo se activa en el tercer intento, no antes."""
        for _ in range(2):
            self.login("mesero1", "clave-mala")

        response = self.login("mesero1", self.password)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_los_registros_de_auditoria_son_inmutables(self):
        """Ningún perfil puede modificar ni eliminar un registro de auditoría."""
        self.login("mesero1", self.password)
        evento = AuditEvent.objects.first()

        with self.assertRaises(NotImplementedError):
            evento.description = "modificado"
            evento.save()

        with self.assertRaises(NotImplementedError):
            evento.delete()
