"""
Carga datos de prueba para demostraciones: sedes, proveedores, productos,
inventario, mesas, usuarios y algunos pedidos.

Uso:
    python manage.py seed_demo --password <clave-de-los-usuarios-demo>

Se puede ejecutar varias veces: lo que ya existe no se duplica. Las entradas de
inventario y los descuentos por pedido pasan por los servicios del módulo de
Inventario, de modo que stock, movimientos y auditoría quedan coherentes.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.inventory.services import discount_for_order, register_entry
from apps.locations.models import Venue
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.suppliers.models import Supplier
from apps.tables.models import Table, TableStatus

VENUES = [
    ("Galería", "Cra. 24 #53-20, Galerías, Bogotá", "galeria"),
    ("Zona T", "Cl. 82 #12-15, Zona T, Bogotá", "zonat"),
    ("Modelia", "Cra. 75 #24C-40, Modelia, Bogotá", "modelia"),
]

SUPPLIERS = [
    ("Bavaria S.A.", "6016389000", "pedidos@bavaria-demo.co"),
    ("Licores de Colombia", "6017451200", "ventas@licorescol-demo.co"),
    ("Postobón", "6014237700", "clientes@postobon-demo.co"),
    ("Café Andino", "3104567890", "contacto@cafeandino-demo.co"),
]

# nombre, tipo, categoría, compra, venta, proveedor
PRODUCTS = [
    ("Club Colombia Dorada", "Bebida", "Cerveza", 2800, 7000, "Bavaria S.A."),
    ("Águila", "Bebida", "Cerveza", 2200, 6000, "Bavaria S.A."),
    ("Poker", "Bebida", "Cerveza", 2100, 5500, "Bavaria S.A."),
    ("Corona", "Bebida", "Cerveza", 3500, 9000, "Bavaria S.A."),
    ("Aguardiente Antioqueño 375 ml", "Bebida", "Licor", 22000, 55000, "Licores de Colombia"),
    ("Ron Viejo de Caldas 375 ml", "Bebida", "Licor", 25000, 60000, "Licores de Colombia"),
    ("Whisky Old Parr 750 ml", "Bebida", "Licor", 95000, 220000, "Licores de Colombia"),
    ("Gaseosa Colombiana", "Bebida", "Gaseosa", 1500, 4000, "Postobón"),
    ("Agua Cristal", "Bebida", "Agua", 1000, 3500, "Postobón"),
    ("Café tinto", "Bebida", "Café", 600, 3000, "Café Andino"),
    ("Capuccino", "Bebida", "Café", 1800, 7000, "Café Andino"),
    ("Papas de paquete", "Comida", "Pasabocas", 1200, 4000, None),
    ("Maní salado", "Comida", "Pasabocas", 900, 3500, None),
]

# Unidades que entran al inventario de cada sede.
INITIAL_STOCK = 48
TABLES_PER_VENUE = 8

# sede, mesa, estado final, [(producto, cantidad), ...]
ORDERS = [
    ("Galería", "Mesa 1", OrderStatus.OPEN, [("Club Colombia Dorada", 4), ("Papas de paquete", 2)]),
    ("Galería", "Mesa 3", OrderStatus.IN_CASHIER, [("Aguardiente Antioqueño 375 ml", 1), ("Agua Cristal", 3)]),
    ("Zona T", "Mesa 2", OrderStatus.OPEN, [("Corona", 6), ("Maní salado", 2)]),
    ("Modelia", "Mesa 5", OrderStatus.OPEN, [("Café tinto", 2), ("Capuccino", 1)]),
]


class Command(BaseCommand):
    help = "Carga datos de prueba (sedes, productos, inventario, mesas, usuarios y pedidos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            required=True,
            help="Contraseña que tendrán los usuarios demo (cajeros y meseros).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).order_by("id").first()
        if admin is None:
            raise CommandError("Primero crea un administrador con: python manage.py createsuperuser")

        venues = {}
        for name, address, _ in VENUES:
            venues[name], _ = Venue.objects.get_or_create(name=name, defaults={"address": address})

        suppliers = {}
        for name, phone, email in SUPPLIERS:
            suppliers[name], _ = Supplier.objects.get_or_create(
                name=name, defaults={"phone": phone, "email": email}
            )

        products = {}
        for name, ptype, category, purchase, sale, supplier in PRODUCTS:
            products[name], _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    "product_type": ptype,
                    "category": category,
                    "purchase_price": purchase,
                    "sale_price": sale,
                    "supplier": suppliers.get(supplier),
                },
            )

        # Inventario inicial: solo para los productos que la sede aún no tiene.
        entries = 0
        for venue in venues.values():
            for product in products.values():
                if not Stock.objects.filter(venue=venue, product=product).exists():
                    register_entry(venue=venue, product=product, quantity=INITIAL_STOCK, performed_by=admin)
                    entries += 1

        for venue in venues.values():
            for number in range(1, TABLES_PER_VENUE + 1):
                Table.objects.get_or_create(venue=venue, identifier=f"Mesa {number}")

        password = options["password"]
        waiters = {}
        created_users = []
        for name, _, slug in VENUES:
            accounts = [
                (f"cajero.{slug}", f"Cajero {name}", Role.CASHIER),
                (f"mesero1.{slug}", f"Mesero 1 {name}", Role.WAITER),
                (f"mesero2.{slug}", f"Mesero 2 {name}", Role.WAITER),
            ]
            for username, full_name, role in accounts:
                user = User.objects.filter(username=username).first()
                if user is None:
                    user = User.objects.create_user(
                        username, password, full_name=full_name, role=role, venue=venues[name]
                    )
                    created_users.append(username)
                if role == Role.WAITER and name not in waiters:
                    waiters[name] = user

        created_orders = 0
        for venue_name, table_id, status, items in ORDERS:
            venue = venues[venue_name]
            table = Table.objects.get(venue=venue, identifier=table_id)
            # Si la mesa ya tiene historial de pedidos, no se vuelve a crear.
            if table.orders.exists():
                continue

            waiter = waiters[venue_name]
            order = Order.objects.create(venue=venue, table=table, waiter=waiter)
            table.status = TableStatus.OCCUPIED
            table.save(update_fields=["status", "updated_at"])

            for product_name, quantity in items:
                product = products[product_name]
                discount_for_order(order=order, product=product, quantity=quantity, performed_by=waiter)
                OrderItem.objects.create(
                    order=order, product=product, quantity=quantity, unit_price=product.sale_price
                )
            order.recalculate_total()

            if status == OrderStatus.IN_CASHIER:
                order.status = OrderStatus.IN_CASHIER
                order.sent_to_cashier_at = timezone.now()
                order.save(update_fields=["status", "sent_to_cashier_at"])
            created_orders += 1

        self.stdout.write(self.style.SUCCESS("Datos de prueba cargados."))
        self.stdout.write(f"  Sedes: {len(venues)} | Proveedores: {len(suppliers)} | Productos: {len(products)}")
        self.stdout.write(f"  Entradas de inventario nuevas: {entries} | Mesas por sede: {TABLES_PER_VENUE}")
        self.stdout.write(f"  Pedidos nuevos: {created_orders}")
        if created_users:
            self.stdout.write(f"  Usuarios creados: {', '.join(created_users)}")
        else:
            self.stdout.write("  Usuarios demo: ya existían (no se cambió su contraseña)")
