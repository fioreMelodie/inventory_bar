"""
Carga de datos de demostración para Bar Inventory APP.

Genera un escenario realista de Café Colombia Bar: las tres sedes, usuarios de
los tres roles, proveedores, catálogo, existencias, mesas y pedidos en
distintos estados.

Los datos se crean a través de los modelos y servicios del sistema, no con
sentencias SQL directas, de modo que las contraseñas quedan cifradas, el stock
genera sus movimientos y todo deja el registro de auditoría correspondiente.

El comando es seguro de repetir: no elimina ni duplica nada. Si un registro ya
existe, lo reutiliza.

Uso:
    python manage.py seed_demo
"""
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.inventory.services import InsufficientStock, discount_for_order, register_entry
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.suppliers.models import Supplier
from apps.tables.models import Table, TableStatus

# Contraseña común de las cuentas de demostración. Solo para desarrollo.
DEMO_PASSWORD = "Cafe2026*Bar"

VENUES = [
    ("Galería", "Calle 59 #9-45, Chapinero"),
    ("Zona T", "Calle 82 #12-18, Chapinero"),
    ("Modelia", "Carrera 73 #25-30, Fontibón"),
]

SUPPLIERS = [
    ("Distribuidora Bavaria", "601 555 1120", "pedidos@bavaria.com.co"),
    ("Industria Licorera de Caldas", "606 555 3344", "ventas@ilc.com.co"),
    ("Fábrica de Licores de Antioquia", "604 555 7788", "contacto@fla.com.co"),
    ("Snacks del Valle", "602 555 9900", "comercial@snacksdelvalle.com"),
]

# (nombre, tipo, categoría, valor de compra, valor de venta, proveedor)
PRODUCTS = [
    ("Cerveza Club Colombia Dorada", "Bebida", "Cerveza", 3500, 9000, "Distribuidora Bavaria"),
    ("Cerveza Águila Original", "Bebida", "Cerveza", 2800, 7000, "Distribuidora Bavaria"),
    ("Cerveza Poker", "Bebida", "Cerveza", 2700, 7000, "Distribuidora Bavaria"),
    ("Cerveza Corona", "Bebida", "Cerveza", 5200, 13000, "Distribuidora Bavaria"),
    ("Aguardiente Antioqueño Sin Azúcar 750ml", "Bebida", "Licor", 52000, 120000,
     "Fábrica de Licores de Antioquia"),
    ("Aguardiente Cristal 750ml", "Bebida", "Licor", 48000, 110000,
     "Industria Licorera de Caldas"),
    ("Ron Viejo de Caldas 750ml", "Bebida", "Licor", 58000, 135000,
     "Industria Licorera de Caldas"),
    ("Whisky Old Parr 750ml", "Bebida", "Licor", 165000, 340000,
     "Industria Licorera de Caldas"),
    ("Tequila José Cuervo 750ml", "Bebida", "Licor", 92000, 195000,
     "Industria Licorera de Caldas"),
    ("Gaseosa Coca-Cola 400ml", "Bebida", "Mezclador", 1800, 5000,
     "Distribuidora Bavaria"),
    ("Agua Tónica Schweppes 300ml", "Bebida", "Mezclador", 2200, 6000,
     "Distribuidora Bavaria"),
    ("Soda Clausen 300ml", "Bebida", "Mezclador", 2000, 5500, "Distribuidora Bavaria"),
    ("Red Bull 250ml", "Bebida", "Energizante", 5500, 14000, "Distribuidora Bavaria"),
    ("Maní salado", "Comida", "Pasaboca", 1200, 4000, "Snacks del Valle"),
    ("Papas fritas naturales", "Comida", "Pasaboca", 1500, 5000, "Snacks del Valle"),
    ("Chicharrón americano", "Comida", "Pasaboca", 1800, 6000, "Snacks del Valle"),
    ("Picada de la casa", "Comida", "Plato", 14000, 38000, "Snacks del Valle"),
]

# (nombre completo, usuario, rol, sede)
USERS = [
    ("Laura Ríos Quintero", "lrios", Role.ADMIN, None),
    ("Ana Gómez Peña", "agomez", Role.CASHIER, "Galería"),
    ("Carlos Mesa Duque", "cmesa", Role.CASHIER, "Zona T"),
    ("Diana Lozano Ruiz", "dlozano", Role.CASHIER, "Modelia"),
    ("Juan Pérez Salas", "jperez", Role.WAITER, "Galería"),
    ("Pedro Díaz Mora", "pdiaz", Role.WAITER, "Galería"),
    ("Sofía Cardona León", "scardona", Role.WAITER, "Zona T"),
    ("Andrés Patiño Gil", "apatino", Role.WAITER, "Zona T"),
    ("Valentina Ospina Cruz", "vospina", Role.WAITER, "Modelia"),
]

TABLES_PER_VENUE = 10


class Command(BaseCommand):
    help = "Carga datos de demostración de Café Colombia Bar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-pedidos",
            action="store_true",
            help="Carga el maestro (sedes, usuarios, catálogo, stock y mesas) sin pedidos.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)  # Resultados reproducibles entre ejecuciones.

        venues = self.create_venues()
        suppliers = self.create_suppliers()
        products = self.create_products(suppliers)
        operator = self.create_users(venues)
        self.create_stock(venues, products, operator)
        tables = self.create_tables(venues)

        if not options["sin_pedidos"]:
            self.create_orders(venues, products, tables)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
        self.stdout.write(f"  Contraseña de todas las cuentas: {DEMO_PASSWORD}")

    # ------------------------------------------------------------------ datos

    def create_venues(self):
        venues = {}
        for name, address in VENUES:
            venue, created = Venue.objects.get_or_create(
                name=name, defaults={"address": address}
            )
            venues[name] = venue
            self.report("Sede", name, created)
        return venues

    def create_suppliers(self):
        suppliers = {}
        for name, phone, email in SUPPLIERS:
            supplier, created = Supplier.objects.get_or_create(
                name=name, defaults={"phone": phone, "email": email}
            )
            suppliers[name] = supplier
            self.report("Proveedor", name, created)
        return suppliers

    def create_products(self, suppliers):
        products = []
        for name, kind, category, purchase, sale, supplier_name in PRODUCTS:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "product_type": kind,
                    "category": category,
                    "purchase_price": purchase,
                    "sale_price": sale,
                    "supplier": suppliers[supplier_name],
                },
            )
            products.append(product)
            self.report("Producto", name, created)
        return products

    def create_users(self, venues):
        """Crea las cuentas y devuelve un Administrador para registrar el stock."""
        operator = None

        for full_name, username, role, venue_name in USERS:
            user = User.objects.filter(username=username).first()
            created = user is None

            if created:
                user = User.objects.create_user(
                    username=username,
                    password=DEMO_PASSWORD,
                    full_name=full_name,
                    role=role,
                    venue=venues[venue_name] if venue_name else None,
                )

            if role == Role.ADMIN and operator is None:
                operator = user

            self.report("Usuario", f"{username} ({role})", created)

        # Si ya existía otro administrador (por ejemplo el superusuario), sirve
        # igual para dejar registrados los movimientos de inventario.
        return operator or User.objects.filter(role=Role.ADMIN).first()

    def create_stock(self, venues, products, operator):
        """
        Registra entradas de mercancía a través del servicio de inventario, de
        modo que cada existencia tenga su movimiento y su evento de auditoría.
        """
        registered = 0

        for venue in venues.values():
            for product in products:
                if product.stock_items.filter(venue=venue).exists():
                    continue

                # Se deja algún producto agotado a propósito, para que la
                # pantalla de inventario muestre el resaltado de stock cero.
                quantity = random.choice([0, 0, 6, 12, 18, 24, 36, 48, 60])
                if quantity == 0:
                    continue

                register_entry(
                    venue=venue,
                    product=product,
                    quantity=quantity,
                    performed_by=operator,
                )
                registered += 1

        self.stdout.write(f"  Entradas de inventario registradas: {registered}")

    def create_tables(self, venues):
        tables = {}
        for venue in venues.values():
            tables[venue.name] = []
            for number in range(1, TABLES_PER_VENUE + 1):
                table, _ = Table.objects.get_or_create(
                    venue=venue, identifier=f"Mesa {number}"
                )
                tables[venue.name].append(table)
        self.stdout.write(f"  Mesas por sede: {TABLES_PER_VENUE}")
        return tables

    def create_orders(self, venues, products, tables):
        """
        Crea pedidos en los dos estados operativos: abiertos en sala y enviados
        a caja, con su stock ya descontado.
        """
        abiertos = 0
        en_caja = 0

        for venue_name, venue_tables in tables.items():
            venue = venues[venue_name]
            waiters = list(User.objects.filter(venue=venue, role=Role.WAITER))
            if not waiters:
                continue

            # Tres mesas ocupadas por sede: dos en sala y una ya en caja.
            for position, table in enumerate(venue_tables[:3]):
                if table.status == TableStatus.OCCUPIED:
                    continue

                order = Order.objects.create(
                    venue=venue,
                    table=table,
                    waiter=random.choice(waiters),
                    status=OrderStatus.OPEN,
                )

                for product in random.sample(products, k=random.randint(2, 4)):
                    quantity = random.randint(1, 4)
                    try:
                        discount_for_order(
                            order=order,
                            product=product,
                            quantity=quantity,
                            performed_by=order.waiter,
                        )
                    except InsufficientStock:
                        # Sin existencias en esa sede, se omite el producto.
                        continue

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price=product.sale_price,
                    )

                order.recalculate_total()

                table.status = TableStatus.OCCUPIED
                table.save(update_fields=["status"])

                # El tercer pedido de cada sede queda esperando en caja.
                if position == 2 and order.items.exists():
                    order.status = OrderStatus.IN_CASHIER
                    order.sent_to_cashier_at = timezone.now()
                    order.save(update_fields=["status", "sent_to_cashier_at"])
                    en_caja += 1
                else:
                    abiertos += 1

        self.stdout.write(f"  Pedidos abiertos en sala: {abiertos}")
        self.stdout.write(f"  Pedidos esperando en caja: {en_caja}")

    # ----------------------------------------------------------------- salida

    def report(self, label, name, created):
        if created:
            self.stdout.write(f"  {label} creado: {name}")
