from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdministrator
from apps.accounts.models import Role
from apps.catalog.models import Product

from .algorithms import (binary_search, bubble_sort, greedy_change, inventory_knapsack,
                         insertion_sort, lexicographically_greatest, quick_sort)


COLOMBIAN_DENOMINATIONS = (100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50)


def integer_parameter(request, name, default, *, minimum=0, maximum=2_000_000):
    raw_value = request.query_params.get(name, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Enter a whole number."})
    if not minimum <= value <= maximum:
        raise ValidationError({name: f"Enter a value from {minimum} to {maximum}."})
    return value


class AlgorithmOverviewView(APIView):
    """Demostración administrativa de siete algoritmos con catálogo real."""
    permission_classes = [IsAdministrator]

    def get(self, request):
        budget = integer_parameter(request, "budget", 100000, minimum=1000)
        change = integer_parameter(request, "change", 0)
        target = request.query_params.get("search", "").strip()
        products = list(Product.objects.filter(is_active=True).values(
            "id", "name", "category", "purchase_price", "sale_price",
        ))
        name_key = lambda item: item["name"].casefold()
        by_name = bubble_sort(products, name_key)
        by_purchase_price = insertion_sort(products, lambda item: item["purchase_price"])
        by_sale_price = quick_sort(products, lambda item: item["sale_price"])
        search_index = binary_search(by_name, target.casefold(), name_key) if target else -1
        selected, profit = inventory_knapsack(products, budget)
        breakdown, remaining = greedy_change(change, COLOMBIAN_DENOMINATIONS)
        return Response({
            "catalog_size": len(products),
            "sorting": {
                "bubble": [{"id": item["id"], "name": item["name"]} for item in by_name],
                "insertion": [{"id": item["id"], "name": item["name"], "purchase_price": item["purchase_price"]} for item in by_purchase_price],
                "quick": [{"id": item["id"], "name": item["name"], "sale_price": item["sale_price"]} for item in by_sale_price],
            },
            "binary_search": {
                "target": target,
                "found": by_name[search_index] if search_index >= 0 else None,
            },
            "knapsack": {
                "budget": budget,
                "selected": [{key: item[key] for key in ("id", "name", "purchase_price", "sale_price", "benefit")} for item in selected],
                "total_cost": sum(item["purchase_price"] for item in selected),
                "total_benefit": profit,
                "weight_unit": 1000,
            },
            "greedy_change": {"amount": change, "breakdown": breakdown, "remaining": remaining},
            "lexicographic_greedy": {"source": target, "result": lexicographically_greatest(target)},
        })


class CashChangeSuggestionView(APIView):
    """Apoyo no transaccional para el cajero antes de confirmar un pago."""

    def get(self, request):
        if request.user.role not in (Role.ADMIN, Role.CASHIER):
            return Response({"detail": "Only cashiers and administrators can access change suggestions."}, status=403)
        amount = integer_parameter(request, "amount", None)
        breakdown, remaining = greedy_change(amount, COLOMBIAN_DENOMINATIONS)
        return Response({"amount": amount, "breakdown": breakdown, "remaining": remaining})
