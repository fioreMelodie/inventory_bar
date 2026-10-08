from pathlib import Path
from django.conf import settings

# Esta carga solo puede ejecutarse sobre una base SQLite exclusiva de QA.
database = settings.DATABASES["default"]
if database["ENGINE"] != "django.db.backends.sqlite3" or not Path(database["NAME"]).name.startswith("bar-inventory-qa-"):
    raise RuntimeError("Use a separate SQLite database named bar-inventory-qa-*")

from apps.accounts.models import User, Role
from apps.locations.models import Venue
from apps.catalog.models import Product
from apps.inventory.models import Stock
from apps.tables.models import Table

venue = Venue.objects.create(name="QA Venue")
for role in Role:
    User.objects.create_user(
        username="qa_" + role.lower(), password="QaPassword2026*",
        full_name="QA " + role.label, role=role, venue=venue,
    )
for index in range(30):
    product = Product.objects.create(
        name=f"QA Product {index:02d}", product_type="Food", category="QA Category",
        purchase_price=1000, sale_price=2000,
    )
    Stock.objects.create(venue=venue, product=product, quantity=10)
for index in range(30):
    Table.objects.create(venue=venue, identifier=f"QA Table {index:02d}")
print("QA: three roles, thirty products and thirty tables created.")
