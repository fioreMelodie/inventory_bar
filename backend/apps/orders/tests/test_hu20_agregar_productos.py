"""
Pruebas de la HU20 - Agregar Productos a un Pedido.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITransactionTestCase

from apps.accounts.models import Role, User
from apps.audit.models import AuditEvent, EventType
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.tables.models import Table, TableStatus


class AddOrderItemTests(APITransactionTestCase):
    """Validación de los criterios de aceptación de la HU20."""

    def setUp(self):
        self.password = "Cafe2026*Bar"
        self.galeria = Venue.objects.create(name="Galería")

        self.mesero = User.objects.create_user(
            username="mesero1", password=self.password,
            full_name="Juan Pérez", role=Role.WAITER, venue=self.galeria,
        )
        self.otro_mesero = User.objects.create_user(
            username="mesero2", password=self.password,
            full_name="Pedro Díaz", role=Role.WAITER, venue=self.galeria,
        )

        self.mesa = Table.objects.create(
            venue=self.galeria, identifier="Mesa 1", status=TableStatus.OCCUPIED
        )
        self.cerveza = Product.objects.create(
            name="Cerveza Club Colombia", product_type="Bebida",
            category="Cerveza", purchase_price=3500, sale_price=9000,
        )
        self.mani = Product.objects.create(
            name="Maní salado", product_type="Comida",
            category="Pasaboca", purchase_price=1200, sale_price=4000,
        )
        Stock.objects.create(venue=self.galeria, product=self.cerveza, quantity=24)
        Stock.objects.create(venue=self.galeria, product=self.mani, quantity=10)

        self.order = Order.objects.create(
            venue=self.galeria, table=self.mesa, waiter=self.mesero
        )
        self.url = reverse("orders:order-add-item", args=[self.order.id])
        self.login(self.mesero)

    def login(self, user):
        response = self.client.post(
            reverse("authentication:login"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def add(self, product, quantity):
        return self.client.post(
            self.url, {"product": product.id, "quantity": quantity}, format="json"
        )

    def test_se_agrega_un_producto_al_pedido(self):
        """El ítem queda registrado con su cantidad."""
        response = self.add(self.cerveza, 3)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = OrderItem.objects.get(order=self.order, product=self.cerveza)
        self.assertEqual(item.quantity, 3)

    def test_el_precio_unitario_se_congela_al_agregar(self):
        """Un cambio posterior de precio no altera el pedido."""
        self.add(self.cerveza, 3)

        self.cerveza.sale_price = 12000
        self.cerveza.save(update_fields=["sale_price"])

        item = OrderItem.objects.get(order=self.order, product=self.cerveza)
        self.assertEqual(item.unit_price, 9000)

    def test_el_total_se_actualiza_automaticamente(self):
        """El total refleja todos los ítems agregados."""
        self.add(self.cerveza, 3)
        response = self.add(self.mani, 2)

        self.order.refresh_from_db()
        self.assertEqual(self.order.total, 3 * 9000 + 2 * 4000)
        self.assertEqual(response.data["total"], 35000)

    def test_el_subtotal_de_cada_linea_se_calcula(self):
        """Cada ítem informa su importe."""
        response = self.add(self.cerveza, 3)

        item = next(
            linea for linea in response.data["items"] if linea["product"] == self.cerveza.id
        )
        self.assertEqual(item["subtotal"], 27000)

    def test_agregar_el_mismo_producto_acumula_cantidades(self):
        """Se puede agregar varias veces; se suman las unidades."""
        self.add(self.cerveza, 3)
        self.add(self.cerveza, 2)

        items = OrderItem.objects.filter(order=self.order, product=self.cerveza)
        self.assertEqual(items.count(), 1)
        self.assertEqual(items.first().quantity, 5)

    def test_el_stock_se_descuenta_al_agregar(self):
        """El inventario refleja el consumo de inmediato."""
        self.add(self.cerveza, 3)

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 21
        )

    def test_no_se_agrega_un_producto_sin_stock_suficiente(self):
        """Se informa stock insuficiente y no se agrega el ítem."""
        response = self.add(self.cerveza, 30)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Not enough stock", response.data["detail"])
        self.assertFalse(OrderItem.objects.filter(order=self.order).exists())

    def test_no_se_agrega_un_producto_con_stock_cero(self):
        """Un producto agotado no puede incorporarse."""
        Stock.objects.filter(venue=self.galeria, product=self.mani).update(quantity=0)

        response = self.add(self.mani, 1)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_el_rechazo_no_altera_el_stock(self):
        """La operación es atómica: o se agrega y descuenta, o nada."""
        self.add(self.cerveza, 30)

        self.assertEqual(
            Stock.objects.get(venue=self.galeria, product=self.cerveza).quantity, 24
        )

    def test_no_se_pueden_agregar_productos_inactivos(self):
        """Un producto con activo=0 no aparece en el módulo de pedidos."""
        inactivo = Product.objects.create(
            name="Cerveza descontinuada", product_type="Bebida", category="Cerveza",
            purchase_price=3000, sale_price=8000, is_active=False,
        )
        Stock.objects.create(venue=self.galeria, product=inactivo, quantity=50)

        response = self.add(inactivo, 1)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_solo_se_modifican_pedidos_abiertos(self):
        """Un pedido enviado a caja ya no admite cambios."""
        self.order.status = OrderStatus.IN_CASHIER
        self.order.save(update_fields=["status"])

        response = self.add(self.cerveza, 1)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(OrderItem.objects.filter(order=self.order).exists())

    def test_la_cantidad_debe_ser_un_entero_positivo(self):
        """No se admiten cantidades nulas, negativas ni fraccionarias."""
        for cantidad in (0, -2, 1.5):
            response = self.add(self.cerveza, cantidad)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_un_mesero_no_modifica_el_pedido_de_otro(self):
        """Cada mesero gestiona sus propios pedidos."""
        self.login(self.otro_mesero)

        response = self.add(self.cerveza, 1)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_el_registro_queda_en_el_log_de_auditoria(self):
        """Se registra qué se agregó y el total resultante."""
        self.add(self.cerveza, 3)

        evento = AuditEvent.objects.filter(event_type=EventType.ORDER_ITEM_ADDED).first()
        self.assertIsNotNone(evento)
        self.assertIn("Cerveza Club Colombia", evento.description)
        self.assertIn("27000", evento.description)
