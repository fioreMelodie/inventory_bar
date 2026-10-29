"""
Pruebas de la HU26 - Consultar Historial de Facturas.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.billing.models import Invoice, PaymentMethod
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class InvoiceHistoryTests(APITestCase):
    """Validación de los criterios de aceptación de la HU26."""

    def setUp(self):
        self.url = reverse("billing:invoice-list")
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
        self.cajero_zona_t = User.objects.create_user(
            username="cajero2", password=self.password,
            full_name="Carlos Mesa", role=Role.CASHIER, venue=self.zona_t,
        )
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )

        self.hoy = timezone.localdate()
        self.ayer = self.hoy - timedelta(days=1)

        self.factura_galeria = self.issue(self.galeria, "Mesa 1", self.cajero)
        self.factura_zona_t = self.issue(self.zona_t, "Mesa 1", self.cajero_zona_t)
        self.factura_antigua = self.issue(
            self.galeria, "Mesa 2", self.cajero, days_ago=5
        )

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def issue(self, venue, identifier, cashier, days_ago=0):
        """Emite una factura directamente, para controlar su fecha."""
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=self.mesero)
        OrderItem.objects.create(
            order=order, product=self.cerveza, quantity=2, unit_price=9000
        )
        order.recalculate_total()
        order.status = OrderStatus.PAID
        order.save(update_fields=["status"])

        sequence = (
            Invoice.objects.filter(venue=venue).count() + 1
        )
        invoice = Invoice.objects.create(
            number=f"F-{venue.id:02d}-{sequence:06d}",
            sequence=sequence,
            venue=venue,
            order=order,
            cashier=cashier,
            payment_method=PaymentMethod.CASH,
            total=order.total,
            amount_received=order.total,
        )

        if days_ago:
            # created_at es auto_now_add. Se ajusta con el gestor base porque
            # el gestor normal bloquea update() para preservar la
            # inmutabilidad de las facturas.
            Invoice._base_manager.filter(pk=invoice.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
            invoice.refresh_from_db()

        return invoice

    def numbers(self, response):
        return [item["number"] for item in response.data["results"]]

    def test_el_cajero_solo_ve_las_facturas_de_su_sede(self):
        """El alcance por sede aplica al historial."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.factura_zona_t.number, self.numbers(response))
        self.assertIn(self.factura_galeria.number, self.numbers(response))

    def test_el_administrador_ve_las_facturas_de_todas_las_sedes(self):
        """El Administrador no está limitado a una sede."""
        self.login(self.admin)

        response = self.client.get(self.url)

        self.assertEqual(len(response.data["results"]), 3)

    def test_filtro_por_sede_para_el_administrador(self):
        """Puede concentrarse en una sede concreta."""
        self.login(self.admin)

        response = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertEqual(self.numbers(response), [self.factura_zona_t.number])

    def test_el_cajero_no_puede_consultar_otra_sede(self):
        """Aunque fuerce el parámetro, recibe solo las suyas."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"venue": self.zona_t.id})

        self.assertNotIn(self.factura_zona_t.number, self.numbers(response))

    def test_filtro_por_rango_de_fechas(self):
        """Acota el historial al periodo solicitado."""
        self.login(self.cajero)

        response = self.client.get(
            self.url, {"date_from": self.hoy.isoformat(), "date_to": self.hoy.isoformat()}
        )

        self.assertIn(self.factura_galeria.number, self.numbers(response))
        self.assertNotIn(self.factura_antigua.number, self.numbers(response))

    def test_filtro_por_numero_de_factura(self):
        """Búsqueda directa por el número del comprobante."""
        self.login(self.cajero)

        response = self.client.get(self.url, {"number": self.factura_galeria.number})

        self.assertEqual(self.numbers(response), [self.factura_galeria.number])

    def test_los_filtros_funcionan_combinados(self):
        """Fecha y sede se aplican simultáneamente."""
        self.login(self.admin)

        response = self.client.get(
            self.url,
            {
                "venue": self.galeria.id,
                "date_from": self.hoy.isoformat(),
                "date_to": self.hoy.isoformat(),
            },
        )

        self.assertEqual(self.numbers(response), [self.factura_galeria.number])

    def test_se_valida_que_la_fecha_inicial_no_supere_la_final(self):
        """Un rango invertido es un error del usuario."""
        self.login(self.cajero)

        response = self.client.get(
            self.url,
            {"date_from": self.hoy.isoformat(), "date_to": self.ayer.isoformat()},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_historial_cubre_desde_el_inicio_del_sistema(self):
        """Sin filtros se devuelven también las facturas antiguas."""
        self.login(self.cajero)

        response = self.client.get(self.url)

        self.assertIn(self.factura_antigua.number, self.numbers(response))

    def test_el_listado_informa_los_datos_del_historial(self):
        """Número, fecha, mesa, total y método de pago."""
        self.login(self.cajero)

        factura = self.client.get(self.url).data["results"][0]

        for campo in ("number", "created_at", "table_identifier", "total",
                      "payment_method_label"):
            self.assertIn(campo, factura)

    def test_no_se_pueden_editar_ni_eliminar_desde_el_historial(self):
        """El historial es de consulta."""
        self.login(self.admin)
        detalle = reverse("billing:invoice-detail", args=[self.factura_galeria.id])

        for metodo in (self.client.patch, self.client.delete):
            self.assertEqual(
                metodo(detalle, {}, format="json").status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            )

    def test_el_mesero_no_accede_al_historial(self):
        """La facturación es de Cajero y Administrador."""
        self.login(self.mesero)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
