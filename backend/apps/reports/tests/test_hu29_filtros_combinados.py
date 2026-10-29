"""
Pruebas de la HU29 - Filtrar Reporte por Criterios Combinados.
"""
import time
from datetime import timedelta

from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class CombinedFiltersTests(APITestCase):
    """Validación de los criterios de aceptación de la HU29."""

    def setUp(self):
        self.url = reverse("reports:sales")
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

        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        self.aguardiente = Product.objects.create(
            name="Aguardiente Antioqueño", product_type="Bebida",
            category="Licor", purchase_price=52000, sale_price=120000,
        )

        self.hoy = timezone.localdate()
        self.ayer = self.hoy - timedelta(days=1)
        self.contador = 0

        # Escenario cruzado: dos sedes, dos productos y dos días.
        self.sell(self.galeria, self.cerveza, 4)
        self.sell(self.galeria, self.aguardiente, 1)
        self.sell(self.zona_t, self.cerveza, 9)
        self.sell(self.galeria, self.cerveza, 7, days_ago=1)

        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def sell(self, venue, product, quantity, days_ago=0):
        self.contador += 1
        table = Table.objects.create(
            venue=venue, identifier=f"Mesa {self.contador}", status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=self.mesero)
        OrderItem.objects.create(
            order=order, product=product, quantity=quantity,
            unit_price=product.sale_price, unit_cost=product.purchase_price,
        )
        order.recalculate_total()
        order.status = OrderStatus.PAID
        order.paid_at = timezone.now() - timedelta(days=days_ago)
        order.save(update_fields=["status", "paid_at"])
        return order

    def report(self, **params):
        payload = {"date_from": self.ayer.isoformat(), "date_to": self.hoy.isoformat()}
        payload.update(params)
        return self.client.get(self.url, payload)

    def test_cada_filtro_adicional_reduce_el_resultado(self):
        """Los filtros funcionan de forma aditiva."""
        sin_filtros = self.report().data["summary"]["quantity"]
        por_sede = self.report(venue=self.galeria.id).data["summary"]["quantity"]
        por_sede_y_producto = self.report(
            venue=self.galeria.id, product=self.cerveza.id
        ).data["summary"]["quantity"]
        todo_combinado = self.report(
            venue=self.galeria.id,
            product=self.cerveza.id,
            date_from=self.hoy.isoformat(),
        ).data["summary"]["quantity"]

        self.assertEqual(sin_filtros, 21)
        self.assertEqual(por_sede, 12)
        self.assertEqual(por_sede_y_producto, 11)
        self.assertEqual(todo_combinado, 4)

    def test_se_combinan_fecha_sede_producto_y_categoria(self):
        """Los cuatro filtros se aplican simultáneamente."""
        response = self.report(
            venue=self.galeria.id,
            product=self.aguardiente.id,
            category="Licor",
            date_from=self.hoy.isoformat(),
        )

        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["product_name"], "Aguardiente Antioqueño")

    def test_una_combinacion_contradictoria_no_devuelve_registros(self):
        """Producto y categoría que no coinciden dan resultado vacío."""
        response = self.report(product=self.cerveza.id, category="Licor")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_el_filtro_de_fecha_es_obligatorio(self):
        """Sin rango no se genera el reporte."""
        for parametros in ({}, {"date_from": self.hoy.isoformat()},
                           {"date_to": self.hoy.isoformat()}):
            response = self.client.get(self.url, parametros)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_los_demas_filtros_son_opcionales(self):
        """Solo con fechas el reporte se genera."""
        response = self.report()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_se_valida_que_la_fecha_inicial_no_supere_la_final(self):
        """Un rango invertido se rechaza con un mensaje claro."""
        response = self.report(
            date_from=self.hoy.isoformat(), date_to=self.ayer.isoformat()
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("start date", response.data["detail"])

    def test_los_resultados_se_ordenan_por_fecha_descendente(self):
        """La fila más reciente aparece primero."""
        fechas = [fila["date"] for fila in self.report().data["results"]]

        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_una_sede_inexistente_devuelve_error(self):
        """No se devuelven datos de otra sede por un filtro inválido."""
        response = self.report(venue=9999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_un_producto_inexistente_devuelve_error(self):
        """Mismo criterio para el filtro de producto."""
        response = self.report(product=9999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_la_combinacion_de_filtros_no_multiplica_las_consultas(self):
        """
        El rendimiento no depende del número de filtros: el reporte se resuelve
        con una sola consulta de agregación, con o sin filtros.
        """
        self.client.get(self.url, {"date_from": self.ayer.isoformat(),
                                   "date_to": self.hoy.isoformat()})

        with CaptureQueriesContext(connection) as sin_filtros:
            self.report()

        with CaptureQueriesContext(connection) as con_filtros:
            self.report(
                venue=self.galeria.id, product=self.cerveza.id, category="Cerveza"
            )

        # Los filtros añaden como mucho la búsqueda de sede y producto.
        self.assertLessEqual(len(con_filtros.captured_queries),
                             len(sin_filtros.captured_queries) + 2)

    def test_el_reporte_responde_en_menos_de_dos_segundos(self):
        """Requisito no funcional de rendimiento."""
        for numero in range(40):
            self.sell(self.galeria, self.cerveza, 1, days_ago=numero % 2)

        inicio = time.perf_counter()
        response = self.report(venue=self.galeria.id, category="Cerveza")
        transcurrido = time.perf_counter() - inicio

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(transcurrido, 2)
