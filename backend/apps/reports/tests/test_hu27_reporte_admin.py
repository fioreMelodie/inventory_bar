"""
Pruebas de la HU27 - Generar Reporte de Ventas, Administrador (Todas las Sedes).
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class AdminSalesReportTests(APITestCase):
    """Validación de los criterios de aceptación de la HU27."""

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
        self.login(self.admin)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def sell(self, venue, product, quantity, *, identifier="Mesa 1", status_=OrderStatus.PAID,
             days_ago=0):
        """Registra una venta ya pagada con los valores congelados del ítem."""
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=self.mesero)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.sale_price,
            unit_cost=product.purchase_price,
        )
        order.recalculate_total()
        order.status = status_
        order.paid_at = (
            timezone.now() - timedelta(days=days_ago)
            if status_ == OrderStatus.PAID
            else None
        )
        order.save(update_fields=["status", "paid_at"])
        return order

    def report(self, **params):
        payload = {"date_from": self.hoy.isoformat(), "date_to": self.hoy.isoformat()}
        payload.update(params)
        return self.client.get(self.url, payload)

    def test_el_reporte_consolida_todas_las_sedes(self):
        """Sin filtro de sede se obtiene el consolidado."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.zona_t, self.cerveza, 2)

        response = self.report()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["venue_name"], "All venues")
        self.assertEqual(response.data["summary"]["quantity"], 5)

    def test_el_reporte_puede_acotarse_a_una_sede(self):
        """El Administrador elige la sede."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.zona_t, self.cerveza, 2)

        response = self.report(venue=self.zona_t.id)

        self.assertEqual(response.data["venue_name"], "Zona T")
        self.assertEqual(response.data["summary"]["quantity"], 2)

    def test_el_reporte_calcula_la_ganancia(self):
        """Ganancia = valor de venta menos valor de compra."""
        self.sell(self.galeria, self.cerveza, 4)

        fila = self.report().data["results"][0]

        self.assertEqual(fila["quantity"], 4)
        self.assertEqual(fila["sale_value"], 36000)
        self.assertEqual(fila["purchase_value"], 14000)
        self.assertEqual(fila["profit"], 22000)

    def test_el_reporte_informa_los_campos_requeridos(self):
        """Fecha, sede, producto, cantidad, compra, venta y ganancia."""
        self.sell(self.galeria, self.cerveza, 1)

        fila = self.report().data["results"][0]

        for campo in ("date", "venue_name", "product_name", "quantity",
                      "purchase_value", "sale_value", "profit"):
            self.assertIn(campo, fila)

    def test_solo_se_incluyen_pedidos_pagados(self):
        """Un pedido abierto o en caja no es una venta."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.galeria, self.cerveza, 10, identifier="Mesa 2",
                  status_=OrderStatus.IN_CASHIER)
        self.sell(self.galeria, self.cerveza, 7, identifier="Mesa 3",
                  status_=OrderStatus.OPEN)

        response = self.report()

        self.assertEqual(response.data["summary"]["quantity"], 3)

    def test_filtro_por_producto(self):
        """Acota el reporte a un producto concreto."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.galeria, self.aguardiente, 1, identifier="Mesa 2")

        response = self.report(product=self.aguardiente.id)

        nombres = [fila["product_name"] for fila in response.data["results"]]
        self.assertEqual(nombres, ["Aguardiente Antioqueño"])

    def test_filtro_por_categoria(self):
        """Acota el reporte a una categoría."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.galeria, self.aguardiente, 1, identifier="Mesa 2")

        response = self.report(category="Licor")

        nombres = [fila["product_name"] for fila in response.data["results"]]
        self.assertEqual(nombres, ["Aguardiente Antioqueño"])

    def test_filtro_por_rango_de_fechas(self):
        """Las ventas fuera del rango no se incluyen."""
        self.sell(self.galeria, self.cerveza, 3)
        self.sell(self.galeria, self.cerveza, 8, identifier="Mesa 2", days_ago=10)

        response = self.report()

        self.assertEqual(response.data["summary"]["quantity"], 3)

    def test_el_historial_no_tiene_limite(self):
        """Con el rango adecuado se alcanzan las ventas antiguas."""
        self.sell(self.galeria, self.cerveza, 8, days_ago=300)

        response = self.report(
            date_from=(self.hoy - timedelta(days=400)).isoformat()
        )

        self.assertEqual(response.data["summary"]["quantity"], 8)

    def test_el_reporte_usa_los_valores_congelados_de_la_venta(self):
        """Un cambio posterior de precio no altera el histórico."""
        self.sell(self.galeria, self.cerveza, 2)

        self.cerveza.sale_price = 20000
        self.cerveza.purchase_price = 9000
        self.cerveza.save(update_fields=["sale_price", "purchase_price"])

        fila = self.report().data["results"][0]

        self.assertEqual(fila["sale_value"], 18000)
        self.assertEqual(fila["purchase_value"], 7000)

    def test_el_rango_de_fechas_es_obligatorio(self):
        """Sin fechas no se genera el reporte."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_mesero_no_accede_a_los_reportes(self):
        """El módulo es de Administrador y Cajero."""
        self.login(self.mesero)

        response = self.report()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
