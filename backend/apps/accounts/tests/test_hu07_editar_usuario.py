"""
Pruebas de la HU07 - Editar Usuario.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.authentication.models import UserSession
from apps.locations.models import Venue


class UpdateUserTests(APITestCase):
    """Validación de los criterios de aceptación de la HU07."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")
        self.modelia = Venue.objects.create(name="Modelia")

        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            full_name="Laura Ríos",
            role=Role.ADMIN,
        )
        self.mesero = User.objects.create_user(
            username="mesero1",
            password=self.password,
            full_name="Juan Pérez",
            role=Role.WAITER,
            venue=self.galeria,
        )
        self.url = reverse("accounts:user-detail", args=[self.mesero.id])
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def test_el_administrador_actualiza_los_datos_del_usuario(self):
        """Se pueden modificar nombre, rol y sede sin recrear la cuenta."""
        response = self.client.patch(
            self.url,
            {"full_name": "Juan Pérez Gómez", "role": Role.CASHIER, "venue": self.modelia.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.full_name, "Juan Pérez Gómez")
        self.assertEqual(self.mesero.role, Role.CASHIER)
        self.assertEqual(self.mesero.venue, self.modelia)

    def test_el_nombre_de_usuario_sigue_siendo_unico_al_editarlo(self):
        """No se admite reutilizar el usuario de otra cuenta."""
        response = self.client.patch(self.url, {"username": "admin1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.username, "mesero1")

    def test_conservar_el_propio_usuario_no_se_considera_duplicado(self):
        """Editar otros campos sin cambiar el usuario no debe fallar."""
        response = self.client.patch(
            self.url, {"username": "mesero1", "full_name": "Juan P."}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_la_nueva_contrasena_se_almacena_cifrada(self):
        """El cambio de contraseña se cifra de inmediato."""
        response = self.client.patch(self.url, {"password": "NuevaClave2026*"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesero.refresh_from_db()
        self.assertNotEqual(self.mesero.password, "NuevaClave2026*")
        self.assertTrue(self.mesero.check_password("NuevaClave2026*"))

    def test_la_contrasena_no_es_obligatoria_al_editar(self):
        """Si no se envía contraseña, la actual se conserva."""
        self.client.patch(self.url, {"full_name": "Juan P."}, format="json")

        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.check_password(self.password))

    def test_el_administrador_no_puede_editar_su_propio_rol(self):
        """Solo otro Administrador puede cambiar el rol de una cuenta admin."""
        url = reverse("accounts:user-detail", args=[self.admin.id])

        response = self.client.patch(url, {"role": Role.CASHIER}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.ADMIN)

    def test_el_administrador_puede_editar_sus_otros_datos(self):
        """La restricción aplica al rol, no al resto de los campos."""
        url = reverse("accounts:user-detail", args=[self.admin.id])

        response = self.client.patch(url, {"full_name": "Laura Ríos Díaz"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_otro_administrador_si_puede_cambiar_el_rol(self):
        """El cambio de rol lo realiza un Administrador distinto."""
        otro_admin = User.objects.create_user(
            username="admin2",
            password=self.password,
            full_name="Carlos Mesa",
            role=Role.ADMIN,
        )
        self.login(otro_admin)
        url = reverse("accounts:user-detail", args=[self.admin.id])

        response = self.client.patch(
            url, {"role": Role.CASHIER, "venue": self.galeria.id}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_el_cambio_de_rol_y_sede_aplica_desde_la_proxima_sesion(self):
        """La sesión activa conserva el rol y la sede con los que se creó."""
        self.client.credentials()
        datos_sesion = self.login(self.mesero)
        sesion = UserSession.objects.get(id=datos_sesion["session_id"])

        self.login(self.admin)
        self.client.patch(
            self.url, {"role": Role.CASHIER, "venue": self.modelia.id}, format="json"
        )

        sesion.refresh_from_db()
        self.assertEqual(sesion.role, Role.WAITER)
        self.assertEqual(sesion.venue, self.galeria)

    def test_el_cambio_de_sede_no_afecta_el_historial_previo(self):
        """Los registros de auditoría del usuario permanecen intactos."""
        eventos_previos = AuditEvent.objects.filter(user=self.mesero).count()

        self.client.patch(self.url, {"venue": self.modelia.id}, format="json")

        self.assertEqual(
            AuditEvent.objects.filter(user=self.mesero).count(), eventos_previos
        )

    def test_la_auditoria_registra_el_valor_anterior_y_el_nuevo(self):
        """Se registra campo modificado, valor anterior y valor nuevo."""
        self.client.patch(self.url, {"venue": self.modelia.id}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.USER_UPDATED).first()
        self.assertIsNotNone(evento)
        self.assertIn("Galería", evento.description)
        self.assertIn("Modelia", evento.description)

    def test_la_auditoria_no_registra_el_valor_de_la_contrasena(self):
        """El log deja constancia del cambio, nunca del valor."""
        self.client.patch(self.url, {"password": "NuevaClave2026*"}, format="json")

        evento = AuditEvent.objects.filter(event_type=EventType.USER_UPDATED).first()
        self.assertIn("password: actualizada", evento.description)
        self.assertNotIn("NuevaClave2026*", evento.description)

    def test_un_cajero_no_puede_editar_usuarios(self):
        """La gestión de cuentas es exclusiva del Administrador."""
        cajero = User.objects.create_user(
            username="cajero1",
            password=self.password,
            full_name="Ana Gómez",
            role=Role.CASHIER,
            venue=self.galeria,
        )
        self.login(cajero)

        response = self.client.patch(self.url, {"full_name": "Otro"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_se_puede_dejar_sin_sede_a_un_mesero(self):
        """La sede sigue siendo obligatoria para Cajero y Mesero."""
        response = self.client.patch(self.url, {"venue": None}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
