"""
Pruebas de la HU25 - Generar Factura.
"""
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


class InvoiceGenerationTests(APITestCase):
    """Validación de los criterios de aceptación de la HU25."""

    def setUp(self):
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
        self.mani = Product.objects.create(
            name="Maní salado", product_type="Comida",
            category="Pasaboca", purchase_price=1200, sale_price=4000,
        )

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def build_order(self, venue, identifier, waiter=None):
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(
            venue=venue, table=table, waiter=waiter or self.mesero
        )
        OrderItem.objects.create(
            order=order, product=self.cerveza, quantity=3, unit_price=9000
        )
        OrderItem.objects.create(
            order=order, product=self.mani, quantity=2, unit_price=4000
        )
        order.recalculate_total()
        order.status = OrderStatus.IN_CASHIER
        order.sent_to_cashier_at = timezone.now()
        order.save(update_fields=["status", "sent_to_cashier_at"])
        return order

    def charge(self, order, amount=40000):
        return self.client.post(
            reverse("billing:charge-order", args=[order.id]),
            {"payment_method": PaymentMethod.CASH, "amount_received": amount},
            format="json",
        )

    def test_la_factura_se_genera_automaticamente(self):
        """No requiere ninguna acción manual adicional al pago."""
        self.login(self.cajero)
        order = self.build_order(self.galeria, "Mesa 1")

        self.charge(order)

        self.assertTrue(Invoice.objects.filter(order=order).exists())

    def test_la_factura_contiene_la_informacion_de_la_transaccion(self):
        """Número, fecha, sede, mesa, mesero, cajero, ítems, total y método."""
        self.login(self.cajero)
        order = self.build_order(self.galeria, "Mesa 1")

        response = self.charge(order)

        self.assertIsNotNone(response.data["number"])
        self.assertIsNotNone(response.data["created_at"])
        self.assertEqual(response.data["venue_name"], "Galería")
        self.assertEqual(response.data["table_identifier"], "Mesa 1")
        self.assertEqual(response.data["waiter_name"], "Juan Pérez")
        self.assertEqual(response.data["cashier_name"], "Ana Gómez")
        self.assertEqual(response.data["payment_method_label"], "Efectivo")
        self.assertEqual(response.data["total"], 35000)

    def test_la_factura_detalla_productos_cantidades_y_precios(self):
        """Cada línea con su cantidad, precio unitario y subtotal."""
        self.login(self.cajero)
        order = self.build_order(self.galeria, "Mesa 1")

        response = self.charge(order)

        items = {item["product_name"]: item for item in response.data["items"]}
        self.assertEqual(items["Cerveza Club Colombia"]["quantity"], 3)
        self.assertEqual(items["Cerveza Club Colombia"]["unit_price"], 9000)
        self.assertEqual(items["Cerveza Club Colombia"]["subtotal"], 27000)
        self.assertEqual(items["Maní salado"]["subtotal"], 8000)

    def test_el_numero_de_factura_es_secuencial_por_sede(self):
        """Cada sede lleva su propio consecutivo."""
        self.login(self.cajero)
        primera = self.charge(self.build_order(self.galeria, "Mesa 1")).data
        segunda = self.charge(self.build_order(self.galeria, "Mesa 2")).data

        self.login(self.cajero_zona_t)
        otra_sede = self.charge(self.build_order(self.zona_t, "Mesa 1")).data

        self.assertEqual(Invoice.objects.get(number=primera["number"]).sequence, 1)
        self.assertEqual(Invoice.objects.get(number=segunda["number"]).sequence, 2)
        # La otra sede arranca de nuevo en uno.
        self.assertEqual(Invoice.objects.get(number=otra_sede["number"]).sequence, 1)

    def test_el_numero_de_factura_es_unico_en_el_sistema(self):
        """Aunque el consecutivo se repita entre sedes, el número no."""
        self.login(self.cajero)
        primera = self.charge(self.build_order(self.galeria, "Mesa 1")).data
        self.login(self.cajero_zona_t)
        otra = self.charge(self.build_order(self.zona_t, "Mesa 1")).data

        self.assertNotEqual(primera["number"], otra["number"])
        self.assertEqual(Invoice.objects.count(), 2)

    def test_la_factura_queda_disponible_para_consulta_inmediata(self):
        """Se puede abrir enseguida desde el panel de facturación."""
        self.login(self.cajero)
        order = self.build_order(self.galeria, "Mesa 1")
        creada = self.charge(order).data

        response = self.client.get(reverse("billing:invoice-detail", args=[creada["id"]]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["number"], creada["number"])

    def test_el_cajero_no_ve_facturas_de_otra_sede(self):
        """El alcance por sede aplica a la facturación."""
        self.login(self.cajero_zona_t)
        ajena = self.charge(self.build_order(self.zona_t, "Mesa 1")).data

        self.login(self.cajero)
        response = self.client.get(reverse("billing:invoice-detail", args=[ajena["id"]]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_el_administrador_ve_facturas_de_todas_las_sedes(self):
        """El Administrador no está limitado a una sede."""
        self.login(self.cajero_zona_t)
        factura = self.charge(self.build_order(self.zona_t, "Mesa 1")).data

        self.login(self.admin)
        response = self.client.get(reverse("billing:invoice-detail", args=[factura["id"]]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_las_facturas_no_pueden_modificarse_desde_la_api(self):
        """Ningún perfil puede editarlas ni anularlas."""
        self.login(self.admin)
        self.login(self.cajero)
        factura = self.charge(self.build_order(self.galeria, "Mesa 1")).data
        url = reverse("billing:invoice-detail", args=[factura["id"]])

        for metodo in (self.client.patch, self.client.put, self.client.delete):
            response = metodo(url, {"total": 1}, format="json")
            self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_las_facturas_no_pueden_modificarse_en_el_modelo(self):
        """La inmutabilidad se garantiza también fuera de la API."""
        self.login(self.cajero)
        self.charge(self.build_order(self.galeria, "Mesa 1"))
        factura = Invoice.objects.get()

        with self.assertRaises(NotImplementedError):
            factura.total = 1
            factura.save()

        with self.assertRaises(NotImplementedError):
            factura.delete()

    def test_el_mesero_no_accede_a_las_facturas(self):
        """La facturación es visible para Cajero y Administrador."""
        self.login(self.cajero)
        factura = self.charge(self.build_order(self.galeria, "Mesa 1")).data

        self.login(self.mesero)
        response = self.client.get(reverse("billing:invoice-detail", args=[factura["id"]]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
