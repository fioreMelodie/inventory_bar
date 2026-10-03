"""
Pruebas de la HU17 - Crear y Configurar Mesas por Sede.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.locations.models import Venue
from apps.tables.models import Table, TableStatus


class TableConfigurationTests(APITestCase):
    """Validación de los criterios de aceptación de la HU17."""

    def setUp(self):
        self.url = reverse("tables:table-list")
        self.password = "Cafe2026*Bar"

        self.galeria = Venue.objects.create(name="Galería")
        self.zona_t = Venue.objects.create(name="Zona T")

        self.admin = User.objects.create_user(
            username="admin1", password=self.password,
            full_name="Laura Ríos", role=Role.ADMIN,
        )
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_el_administrador_crea_una_mesa(self):
        """La mesa queda registrada en la sede seleccionada."""
        response = self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        table = Table.objects.get(id=response.data["id"])
        self.assertEqual(table.identifier, "Mesa 1")
        self.assertEqual(table.venue, self.galeria)

    def test_las_mesas_se_crean_siempre_libres(self):
        """El estado inicial es LIBRE."""
        response = self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        self.assertEqual(response.data["status"], TableStatus.FREE)
        self.assertTrue(Table.objects.get(id=response.data["id"]).is_free)

    def test_el_estado_no_se_puede_asignar_a_mano(self):
        """El estado lo determinan los pedidos, no el formulario."""
        response = self.client.post(
            self.url,
            {"venue": self.galeria.id, "identifier": "Mesa 1", "status": TableStatus.OCCUPIED},
            format="json",
        )

        self.assertEqual(response.data["status"], TableStatus.FREE)

    def test_el_identificador_es_unico_dentro_de_la_sede(self):
        """No puede haber dos 'Mesa 1' en la misma sede."""
        self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        response = self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Table.objects.filter(venue=self.galeria).count(), 1)

    def test_el_mismo_identificador_puede_repetirse_en_otra_sede(self):
        """Puede haber Mesa 1 en Galería y Mesa 1 en Zona T."""
        self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        response = self.client.post(
            self.url, {"venue": self.zona_t.id, "identifier": "Mesa 1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Table.objects.filter(identifier="Mesa 1").count(), 2)

    def test_el_identificador_es_obligatorio(self):
        """Sin identificador la mesa no se crea."""
        response = self.client.post(self.url, {"venue": self.galeria.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("identifier", response.data)

    def test_no_hay_limite_de_mesas_por_sede(self):
        """El Administrador crea tantas mesas como requiera la operación."""
        for numero in range(1, 26):
            response = self.client.post(
                self.url,
                {"venue": self.galeria.id, "identifier": f"Mesa {numero}"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Table.objects.filter(venue=self.galeria).count(), 25)

    def test_se_puede_editar_el_identificador_de_una_mesa_libre(self):
        """La mesa sin pedidos activos se puede renombrar."""
        creada = self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )
        detalle = reverse("tables:table-detail", args=[creada.data["id"]])

        response = self.client.patch(detalle, {"identifier": "Mesa 1A"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Table.objects.get(id=creada.data["id"]).identifier, "Mesa 1A")

    def test_no_se_puede_renombrar_una_mesa_ocupada(self):
        """Una mesa con pedido activo no admite cambio de identificador."""
        table = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )
        detalle = reverse("tables:table-detail", args=[table.id])

        response = self.client.patch(detalle, {"identifier": "Mesa 9"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        table.refresh_from_db()
        self.assertEqual(table.identifier, "Mesa 1")

    def test_las_mesas_se_inactivan_no_se_eliminan(self):
        """No existe eliminación: la mesa se inactiva conservando su histórico."""
        table = Table.objects.create(venue=self.galeria, identifier="Mesa 1")
        detalle = reverse("tables:table-detail", args=[table.id])

        eliminacion = self.client.delete(detalle)
        inactivacion = self.client.post(
            reverse("tables:table-deactivate", args=[table.id]), {}, format="json"
        )

        self.assertEqual(eliminacion.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(inactivacion.status_code, status.HTTP_200_OK)
        table.refresh_from_db()
        self.assertFalse(table.is_active)
        self.assertTrue(Table.objects.filter(id=table.id).exists())

    def test_no_se_inactiva_una_mesa_ocupada(self):
        """Una mesa con pedido activo no puede retirarse de la operación."""
        table = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )

        response = self.client.post(
            reverse("tables:table-deactivate", args=[table.id]), {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        table.refresh_from_db()
        self.assertTrue(table.is_active)

    def test_solo_el_administrador_configura_mesas(self):
        """El Mesero no parametriza mesas."""
        self.login(self.mesero)

        response = self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 99"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_mesero_solo_ve_las_mesas_de_su_sede(self):
        """El alcance por sede aplica también a las mesas."""
        Table.objects.create(venue=self.galeria, identifier="Mesa 1")
        Table.objects.create(venue=self.zona_t, identifier="Mesa 1")
        self.login(self.mesero)

        response = self.client.get(self.url)

        sedes = {item["venue"] for item in response.data["results"]}
        self.assertEqual(sedes, {self.galeria.id})

    def test_la_creacion_queda_en_el_log_de_auditoria(self):
        """Se registra la creación de la mesa."""
        self.client.post(
            self.url, {"venue": self.galeria.id, "identifier": "Mesa 1"}, format="json"
        )

        evento = AuditEvent.objects.filter(event_type=EventType.TABLE_CREATED).first()
        self.assertIsNotNone(evento)
        self.assertIn("Mesa 1", evento.description)
        self.assertIn("Galería", evento.description)
