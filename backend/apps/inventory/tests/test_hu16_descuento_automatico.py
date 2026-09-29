"""
Pruebas de la HU16 - Descuento Automático de Stock al Crear un Pedido.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import MovementType, Stock, StockMovement
from apps.inventory.services import InsufficientStock, discount_for_order
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class StockDiscountTests(APITransactionTestCase):
    """El descuento ocurre al agregar el ítem, no al procesar el pago."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.mesa = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        self.order = Order.objects.create(
            venue=self.galeria, table=self.mesa, waiter=self.mesero
        )

    def test_el_stock_se_descuenta_al_agregar_el_item(self):
        """La cantidad solicitada sale del inventario de la sede."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)

        discount_for_order(
            order=self.order, product=self.cerveza, quantity=6, performed_by=self.mesero
        )

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 18
        )

    def test_sin_stock_suficiente_se_rechaza_la_operacion(self):
        """Se informa stock insuficiente y no se modifica el inventario."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=3)

        with self.assertRaises(InsufficientStock):
            discount_for_order(
                order=self.order, product=self.cerveza, quantity=6,
                performed_by=self.mesero,
            )

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 3
        )
        self.assertFalse(StockMovement.objects.exists())

    def test_no_se_puede_agregar_un_producto_con_stock_cero(self):
        """Un producto agotado no puede incorporarse al pedido."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=0)

        with self.assertRaises(InsufficientStock):
            discount_for_order(
                order=self.order, product=self.cerveza, quantity=1,
                performed_by=self.mesero,
            )

    def test_un_producto_sin_existencias_registradas_se_trata_como_cero(self):
        """Sin registro de stock en la sede no hay unidades disponibles."""
        with self.assertRaises(InsufficientStock) as contexto:
            discount_for_order(
                order=self.order, product=self.cerveza, quantity=1,
                performed_by=self.mesero,
            )

        self.assertEqual(contexto.exception.available, 0)

    def test_se_puede_descontar_todo_el_stock_disponible(self):
        """El límite es la cantidad existente, no una unidad menos."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=5)

        discount_for_order(
            order=self.order, product=self.cerveza, quantity=5, performed_by=self.mesero
        )

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 0
        )

    def test_el_descuento_genera_un_movimiento_negativo(self):
        """La suma de movimientos reconstruye el stock."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)

        discount_for_order(
            order=self.order, product=self.cerveza, quantity=6, performed_by=self.mesero
        )

        movimiento = StockMovement.objects.get()
        self.assertEqual(movimiento.movement_type, MovementType.ORDER_DISCOUNT)
        self.assertEqual(movimiento.quantity, -6)
        self.assertEqual(movimiento.order, self.order)

    def test_el_descuento_queda_en_el_log_de_auditoria(self):
        """Se registra producto, cantidad, pedido, mesero y sede."""
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)

        discount_for_order(
            order=self.order, product=self.cerveza, quantity=6, performed_by=self.mesero
        )

        evento = AuditEvent.objects.filter(event_type=EventType.STOCK_DISCOUNT).first()
        self.assertIsNotNone(evento)
        self.assertEqual(evento.user, self.mesero)
        self.assertIn("Cerveza Club Colombia", evento.description)
        self.assertIn("Galería", evento.description)
        self.assertIn(str(self.order.id), evento.description)

    def test_el_stock_de_otra_sede_no_se_ve_afectado(self):
        """Cada sede mantiene su inventario independiente."""
        zona_t = Venue.objects.create(name="Zona T")
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)
        Stock.objects.create(venue=zona_t, product=self.cerveza, quantity=10)

        discount_for_order(
            order=self.order, product=self.cerveza, quantity=6, performed_by=self.mesero
        )

        self.assertEqual(Stock.objects.get(venue=zona_t, product=self.cerveza).quantity, 10)


class OrderCancellationTests(APITestCase):
    """Si el pedido se cancela estando ABIERTO, el stock se reintegra."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")
        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.mesa = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        self.stock = Stock.objects.create(
            venue=self.galeria, product=self.cerveza, quantity=18
        )
        self.order = Order.objects.create(
            venue=self.galeria, table=self.mesa, waiter=self.mesero
        )
        OrderItem.objects.create(
            order=self.order, product=self.cerveza, quantity=6, unit_price=9000
        )
        self.url = reverse("orders:order-cancel", args=[self.order.id])
        self.login(self.mesero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_la_cancelacion_reintegra_el_stock(self):
        """Las unidades descontadas vuelven al inventario."""
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 24)

    def test_el_pedido_cancelado_no_se_elimina(self):
        """El histórico de pedidos es permanente."""
        self.client.post(self.url, {}, format="json")

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, OrderStatus.CANCELLED)
        self.assertTrue(Order.objects.filter(id=self.order.id).exists())

    def test_la_mesa_vuelve_a_quedar_libre(self):
        """La mesa se libera al cancelar el pedido."""
        self.client.post(self.url, {}, format="json")

        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.status, TableStatus.FREE)

    def test_el_reintegro_genera_un_movimiento_positivo(self):
        """Queda trazabilidad del reintegro."""
        self.client.post(self.url, {}, format="json")

        movimiento = StockMovement.objects.filter(
            movement_type=MovementType.ORDER_RESTORE
        ).first()
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.quantity, 6)
        self.assertEqual(movimiento.order, self.order)

    def test_el_reintegro_queda_en_el_log_de_auditoria(self):
        """Se registra la cancelación y el reintegro."""
        self.client.post(self.url, {}, format="json")

        self.assertTrue(
            AuditEvent.objects.filter(event_type=EventType.STOCK_RESTORE).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(event_type=EventType.ORDER_CANCELLED).exists()
        )

    def test_un_pedido_ya_enviado_a_caja_no_se_cancela(self):
        """Una vez en caja el pedido es inmutable."""
        self.order.status = OrderStatus.IN_CASHIER
        self.order.save(update_fields=["status"])

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 18)

    def test_no_se_cancela_dos_veces_el_mismo_pedido(self):
        """El reintegro no puede duplicarse."""
        self.client.post(self.url, {}, format="json")

        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 24)
