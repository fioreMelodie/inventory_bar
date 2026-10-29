"""
Pruebas de la HU24 - Procesar Pago con Tarjeta (Crédito / Débito).
"""
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.billing.models import Invoice, PaymentMethod
from apps.catalog.models import Product
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class CardPaymentTests(APITestCase):
    """Validación de los criterios de aceptación de la HU24."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")

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

        self.order = self.build_order("Mesa 1")
        self.url = reverse("billing:charge-order", args=[self.order.id])
        self.login(self.cajero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def build_order(self, identifier):
        table = Table.objects.create(
            venue=self.galeria, identifier=identifier, status=TableStatus.OCCUPIED
        )
        order = Order.objects.create(
            venue=self.galeria, table=table, waiter=self.mesero
        )
        OrderItem.objects.create(
            order=order, product=self.cerveza, quantity=3, unit_price=9000
        )
        order.recalculate_total()
        order.status = OrderStatus.IN_CASHIER
        order.sent_to_cashier_at = timezone.now()
        order.save(update_fields=["status", "sent_to_cashier_at"])
        return order

    def pay_card(self, method, *, approved=True, url=None, **extra):
        payload = {"payment_method": method, "card_approved": approved}
        payload.update(extra)
        return self.client.post(url or self.url, payload, format="json")

    def test_pago_con_tarjeta_de_credito(self):
        """Se registra el método utilizado."""
        response = self.pay_card(PaymentMethod.CREDIT_CARD)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(order=self.order)
        self.assertEqual(invoice.payment_method, PaymentMethod.CREDIT_CARD)

    def test_pago_con_tarjeta_debito(self):
        """El débito se distingue del crédito."""
        response = self.pay_card(PaymentMethod.DEBIT_CARD)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Invoice.objects.get(order=self.order).payment_method, PaymentMethod.DEBIT_CARD
        )

    def test_el_cajero_debe_confirmar_la_aprobacion_del_datafono(self):
        """Sin confirmación manual no se registra el pago."""
        response = self.pay_card(PaymentMethod.CREDIT_CARD, approved=False)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("card_approved", response.data)
        self.assertFalse(Invoice.objects.exists())

    def test_el_pago_con_tarjeta_no_registra_monto_ni_cambio(self):
        """El cobro ocurre en el datáfono externo: no hay cambio que calcular."""
        response = self.pay_card(PaymentMethod.CREDIT_CARD)

        self.assertIsNone(response.data["amount_received"])
        self.assertEqual(response.data["change_given"], 0)

    def test_el_monto_enviado_con_tarjeta_se_ignora(self):
        """Aunque se envíe, no se guarda: no aplica al pago con tarjeta."""
        response = self.pay_card(PaymentMethod.DEBIT_CARD, amount_received=50000)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(Invoice.objects.get(order=self.order).amount_received)

    def test_no_se_pueden_combinar_efectivo_y_tarjeta(self):
        """Un pedido se cobra con un único método de pago."""
        invoice_fields = [field.name for field in Invoice._meta.get_fields()]

        # El modelo guarda un solo método; no existe forma de registrar dos.
        self.assertIn("payment_method", invoice_fields)

        self.pay_card(PaymentMethod.CREDIT_CARD)
        segundo = self.client.post(
            self.url,
            {"payment_method": PaymentMethod.CASH, "amount_received": 27000},
            format="json",
        )

        self.assertEqual(segundo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)

    def test_el_pedido_queda_pagado_y_la_mesa_libre(self):
        """Mismo cierre de transacción que en el pago en efectivo."""
        self.pay_card(PaymentMethod.CREDIT_CARD)

        self.order.refresh_from_db()
        self.order.table.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.PAID)
        self.assertEqual(self.order.table.status, TableStatus.FREE)

    def test_el_metodo_queda_en_la_factura_y_en_auditoria(self):
        """Trazabilidad del método de pago utilizado."""
        self.pay_card(PaymentMethod.DEBIT_CARD)

        evento = AuditEvent.objects.filter(
            event_type=EventType.PAYMENT_REGISTERED
        ).first()
        self.assertIsNotNone(evento)
        self.assertIn("Tarjeta débito", evento.description)

    def test_no_se_admite_un_metodo_de_pago_inexistente(self):
        """Solo efectivo, crédito y débito."""
        response = self.client.post(
            self.url,
            {"payment_method": "CRYPTO", "card_approved": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_el_sistema_no_se_integra_con_pasarela_de_pago(self):
        """La factura no guarda datos de ninguna transacción externa."""
        self.pay_card(PaymentMethod.CREDIT_CARD)
        invoice = Invoice.objects.get(order=self.order)

        campos = {field.name for field in Invoice._meta.get_fields()}
        for externo in ("gateway", "authorization_code", "card_number", "transaction_id"):
            self.assertNotIn(externo, campos)
        self.assertEqual(invoice.payment_method, PaymentMethod.CREDIT_CARD)
