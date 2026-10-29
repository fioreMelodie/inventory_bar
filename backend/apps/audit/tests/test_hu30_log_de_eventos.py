"""
Pruebas de la HU30 - Consultar Log de Eventos del Sistema.
"""
import time
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.services import register_entry
from apps.locations.models import Venue


class AuditLogTests(APITestCase):
    """Validación de los criterios de aceptación de la HU30."""

    def setUp(self):
        self.url = reverse("audit:audit-event-list")
        self.password = "Cafe2026*Bar"

        self.galeria = Venue.objects.create(name="Galería")
        self.zona_t = Venue.objects.create(name="Zona T")

        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )
        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.galeria,
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )

        self.hoy = timezone.localdate()
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def events(self, **params):
        return self.client.get(self.url, params)

    def test_el_administrador_consulta_el_log(self):
        """El módulo devuelve los eventos registrados."""
        response = self.events()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_el_log_informa_los_datos_de_trazabilidad(self):
        """Usuario, tipo de evento, entidad, sede, fecha y hora."""
        evento = self.events().data["results"][0]

        for campo in ("username", "event_type", "event_type_label", "entity",
                      "venue", "created_at", "description", "ip_address"):
            self.assertIn(campo, evento)

    def test_se_registran_los_inicios_de_sesion(self):
        """El login queda en el log."""
        response = self.events(event_type=EventType.LOGIN_SUCCESS)

        self.assertGreater(len(response.data["results"]), 0)

    def test_se_registran_las_entradas_de_inventario_con_su_sede(self):
        """Las acciones operativas quedan asociadas a la sede."""
        register_entry(
            venue=self.galeria, product=self.cerveza, quantity=10,
            performed_by=self.cajero,
        )

        evento = self.events(event_type=EventType.STOCK_ENTRY).data["results"][0]

        self.assertEqual(evento["venue"], self.galeria.id)
        self.assertEqual(evento["venue_name"], "Galería")

    def test_filtro_por_usuario(self):
        """Acota el log a las acciones de una persona."""
        register_entry(
            venue=self.galeria, product=self.cerveza, quantity=5,
            performed_by=self.cajero,
        )

        response = self.events(username="cajero1")

        self.assertGreater(len(response.data["results"]), 0)
        for evento in response.data["results"]:
            self.assertIn("cajero1", evento["username"])

    def test_filtro_por_tipo_de_evento(self):
        """Acota el log a un tipo concreto."""
        response = self.events(event_type=EventType.LOGIN_SUCCESS)

        for evento in response.data["results"]:
            self.assertEqual(evento["event_type"], EventType.LOGIN_SUCCESS)

    def test_filtro_por_sede(self):
        """Acota el log a lo ocurrido en una sede."""
        register_entry(
            venue=self.galeria, product=self.cerveza, quantity=5,
            performed_by=self.cajero,
        )
        register_entry(
            venue=self.zona_t, product=self.cerveza, quantity=7,
            performed_by=self.admin,
        )

        response = self.events(venue=self.zona_t.id)

        self.assertGreater(len(response.data["results"]), 0)
        for evento in response.data["results"]:
            self.assertEqual(evento["venue"], self.zona_t.id)

    def test_filtro_por_rango_de_fechas(self):
        """Acota el log al periodo solicitado."""
        antiguo = AuditEvent.objects.create(
            username="admin1", event_type=EventType.LOGIN_SUCCESS,
            description="Evento antiguo",
        )
        AuditEvent._base_manager.filter(pk=antiguo.pk).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        response = self.events(
            date_from=self.hoy.isoformat(), date_to=self.hoy.isoformat()
        )

        descripciones = [item["description"] for item in response.data["results"]]
        self.assertNotIn("Evento antiguo", descripciones)

    def test_los_filtros_se_combinan(self):
        """Usuario, tipo y sede se aplican simultáneamente."""
        register_entry(
            venue=self.galeria, product=self.cerveza, quantity=5,
            performed_by=self.cajero,
        )

        response = self.events(
            username="cajero1",
            event_type=EventType.STOCK_ENTRY,
            venue=self.galeria.id,
        )

        self.assertEqual(len(response.data["results"]), 1)

    def test_se_valida_el_rango_de_fechas(self):
        """La fecha inicial no puede superar a la final."""
        response = self.events(
            date_from=self.hoy.isoformat(),
            date_to=(self.hoy - timedelta(days=1)).isoformat(),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_log_es_inmutable_desde_la_api(self):
        """No se expone ninguna operación de escritura."""
        evento = self.events().data["results"][0]
        detalle = f"{self.url}{evento['id']}/"

        for metodo in (self.client.post, self.client.patch, self.client.delete):
            response = metodo(detalle, {}, format="json")
            self.assertIn(
                response.status_code,
                (status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED),
            )

    def test_el_log_es_inmutable_en_el_modelo(self):
        """Ningún perfil puede alterar un registro de auditoría."""
        evento = AuditEvent.objects.first()

        with self.assertRaises(NotImplementedError):
            evento.description = "alterado"
            evento.save()

        with self.assertRaises(NotImplementedError):
            evento.delete()

    def test_solo_el_administrador_accede_al_modulo(self):
        """Auditoría es exclusivo del Administrador."""
        self.login(self.cajero)

        response = self.events()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_se_ofrecen_los_tipos_de_evento_para_el_filtro(self):
        """La interfaz puebla el selector con los tipos registrables."""
        response = self.client.get(reverse("audit:audit-event-event-types"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        valores = [item["value"] for item in response.data]
        for esperado in (EventType.LOGIN_SUCCESS, EventType.ORDER_OPENED,
                         EventType.PAYMENT_REGISTERED, EventType.STOCK_ENTRY):
            self.assertIn(esperado, valores)

    def test_la_consulta_responde_en_menos_de_dos_segundos(self):
        """Requisito no funcional de rendimiento."""
        AuditEvent.objects.bulk_create([
            AuditEvent(
                username="cajero1", event_type=EventType.LOGIN_SUCCESS,
                venue=self.galeria, description=f"Evento {numero}",
            )
            for numero in range(500)
        ])

        inicio = time.perf_counter()
        response = self.events(venue=self.galeria.id, username="cajero1")
        transcurrido = time.perf_counter() - inicio

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(transcurrido, 2)
