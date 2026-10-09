"""
Pruebas de la HU23 - Procesar Pago en Efectivo.
"""
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.billing.models import Invoice
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class CashPaymentTests(APITestCase):
    """Validación de los criterios de aceptación de la HU23."""

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
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )

        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )

        self.order = self.build_order(self.galeria, "Mesa 1")
        self.url = reverse("billing:charge-order", args=[self.order.id])
        self.login(self.cajero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def build_order(self, venue, identifier, *, in_cashier=True):
        table = Table.objects.create(
            venue=venue, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(venue=venue, table=table, waiter=self.mesero)
        OrderItem.objects.create(
            order=order, product=self.cerveza, quantity=3, unit_price=9000
        )
        order.recalculate_total()

        if in_cashier:
            order.status = OrderStatus.IN_CASHIER
            order.sent_to_cashier_at = timezone.now()
            order.save(update_fields=["status", "sent_to_cashier_at"])

        return order

    def pay(self, amount, order_url=None):
        return self.client.post(
            order_url or self.url,
            {"payment_method": "CASH", "amount_received": amount},
            format="json",
        )

    def test_el_pago_en_efectivo_genera_la_factura(self):
        """Al confirmar se registra el pago y se emite la factura."""
        response = self.pay(30000)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(order=self.order)
        self.assertEqual(invoice.total, 27000)
        self.assertEqual(invoice.payment_method, "CASH")
        self.assertEqual(invoice.cashier, self.cajero)

    def test_el_sistema_calcula_el_cambio(self):
        """Cambio = monto recibido menos total del pedido."""
        response = self.pay(30000)

        self.assertEqual(response.data["change_given"], 3000)
        self.assertEqual(Invoice.objects.get(order=self.order).change_given, 3000)

    def test_el_monto_exacto_no_genera_cambio(self):
        """Pagar justo es válido."""
        response = self.pay(27000)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["change_given"], 0)

    def test_el_monto_recibido_no_puede_ser_menor_al_total(self):
        """No se admite un pago incompleto."""
        response = self.pay(20000)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Invoice.objects.exists())
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.IN_CASHIER)

    def test_el_monto_recibido_es_obligatorio_en_efectivo(self):
        """Sin monto no se puede calcular el cambio."""
        response = self.client.post(self.url, {"payment_method": "CASH"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_pedido_queda_pagado(self):
        """El pedido cambia a estado PAGADO."""
        self.pay(27000)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertIsNotNone(self.order.paid_at)

    def test_la_mesa_queda_libre(self):
        """La mesa se libera automáticamente al registrarse el pago."""
        self.pay(27000)

        self.order.table.refresh_from_db()
        self.assertEqual(self.order.table.status, TableStatus.FREE)

    def test_un_pedido_pagado_no_puede_modificarse(self):
        """Tras el cobro el pedido es definitivo."""
        self.pay(27000)
        self.login(self.mesero)

        response = self.client.post(
            reverse("orders:order-add-item", args=[self.order.id]),
            {"product": self.cerveza.id, "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_se_cobra_dos_veces_el_mismo_pedido(self):
        """El segundo intento se rechaza."""
        self.pay(27000)

        response = self.pay(27000)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)

    def test_no_se_cobra_un_pedido_que_sigue_abierto(self):
        """Solo se cobran pedidos enviados a caja."""
        abierto = self.build_order(self.galeria, "Mesa 2", in_cashier=False)

        response = self.pay(
            27000, reverse("billing:charge-order", args=[abierto.id])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_pedido_cobrado_sale_del_panel_de_pendientes(self):
        """Un pedido cobrado desaparece del panel del cajero (HU22)."""
        self.pay(27000)

        pendientes = self.client.get(
            reverse("orders:order-list"), {"status": OrderStatus.IN_CASHIER}
        ).data["results"]

        self.assertEqual(pendientes, [])

    def test_el_cajero_no_cobra_pedidos_de_otra_sede(self):
        """El alcance por sede aplica también al cobro."""
        ajeno = self.build_order(self.zona_t, "Mesa 1")

        response = self.pay(27000, reverse("billing:charge-order", args=[ajeno.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_mesero_no_puede_cobrar(self):
        """La caja es del Cajero y el Administrador."""
        self.login(self.mesero)

        response = self.pay(27000)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_pago_queda_en_el_log_de_auditoria(self):
        """Se registra el pago con el método y la factura generada."""
        self.pay(27000)

        evento = AuditEvent.objects.filter(
            event_type=EventType.PAYMENT_REGISTERED
        ).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.cajero)
        self.assertIn("Efectivo", evento.description)
        self.assertIn(Invoice.objects.get().number, evento.description)
