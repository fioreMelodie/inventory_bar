"""
Pruebas de la HU28 - Generar Reporte de Ventas, Cajero (Sede Propia).
"""
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class CashierSalesReportTests(APITestCase):
    """Validación de los criterios de aceptación de la HU28."""

    def setUp(self):
        self.url = reverse("reports:sales")
        self.password = "Cafe2026*Bar"

        self.galeria = Venue.objects.create(name="Galería")
        self.zona_t = Venue.objects.create(name="Zona T")

        self.cajero = User.objects.create_user(
            username="cajero1", password=self.password,
            full_name="Ana Gómez", role=Role.CASHIER, venue=self.galeria,
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

        self.sell(self.galeria, self.cerveza, 4, identifier="Mesa 1")
        self.sell(self.galeria, self.aguardiente, 1, identifier="Mesa 2")
        self.sell(self.zona_t, self.cerveza, 9, identifier="Mesa 1")

        self.login(self.cajero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def sell(self, venue, product, quantity, identifier="Mesa 1"):
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=self.mesero)
        OrderItem.objects.create(
            order=order, product=product, quantity=quantity,
            unit_price=product.sale_price, unit_cost=product.purchase_price,
        )
        order.recalculate_total()
        order.status = OrderStatus.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        return order

    def report(self, **params):
        payload = {"date_from": self.hoy.isoformat(), "date_to": self.hoy.isoformat()}
        payload.update(params)
        return self.client.get(self.url, payload)

    def test_el_reporte_del_cajero_es_de_su_sede(self):
        """La sede queda fija a la asignada."""
        response = self.report()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["venue_name"], "Galería")

    def test_el_cajero_no_puede_cambiar_la_sede_del_reporte(self):
        """Aunque envíe otra sede, recibe la suya."""
        response = self.report(venue=self.zona_t.id)

        self.assertEqual(response.data["venue_name"], "Galería")
        # Las 9 unidades vendidas en Zona T no deben aparecer.
        self.assertEqual(response.data["summary"]["quantity"], 5)

    def test_el_reporte_del_cajero_no_incluye_valor_de_compra(self):
        """El costo es información reservada al Administrador."""
        for fila in self.report().data["results"]:
            self.assertNotIn("purchase_value", fila)

    def test_el_reporte_del_cajero_no_incluye_ganancia(self):
        """El margen es información reservada al Administrador."""
        for fila in self.report().data["results"]:
            self.assertNotIn("profit", fila)

    def test_los_totales_del_cajero_tampoco_exponen_el_margen(self):
        """El resumen respeta la misma restricción."""
        resumen = self.report().data["summary"]

        self.assertIn("quantity", resumen)
        self.assertIn("sale_value", resumen)
        self.assertNotIn("purchase_value", resumen)
        self.assertNotIn("profit", resumen)

    def test_el_reporte_del_cajero_informa_fecha_producto_cantidad_y_venta(self):
        """Son los campos habilitados para su rol."""
        fila = self.report().data["results"][0]

        for campo in ("date", "product_name", "quantity", "sale_value"):
            self.assertIn(campo, fila)

    def test_filtro_por_producto_disponible_para_el_cajero(self):
        """Puede acotar por producto."""
        response = self.report(product=self.aguardiente.id)

        nombres = [fila["product_name"] for fila in response.data["results"]]
        self.assertEqual(nombres, ["Aguardiente Antioqueño"])

    def test_solo_se_incluyen_pedidos_pagados(self):
        """Misma regla que en el reporte del Administrador."""
        table = Table.objects.create(
            venue=self.galeria, identifier="Mesa 9", status=TableStatus.OCCUPIED
        )
        pendiente = Order.objects.create(
            venue=self.galeria, table=table, waiter=self.mesero
        )
        OrderItem.objects.create(
            order=pendiente, product=self.cerveza, quantity=50,
            unit_price=9000, unit_cost=3500,
        )
        pendiente.recalculate_total()

        self.assertEqual(self.report().data["summary"]["quantity"], 5)

    def test_un_cajero_sin_sede_no_puede_generar_el_reporte(self):
        """El reporte necesita una sede de referencia."""
        self.cajero.venue = None
        self.cajero.save(update_fields=["venue"])

        response = self.report()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
