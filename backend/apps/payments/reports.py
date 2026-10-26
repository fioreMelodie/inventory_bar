import csv
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdministrator
from apps.accounts.models import Role
from apps.orders.models import OrderStatus

from .filters import filter_invoices
from .models import Invoice
from .serializers import CashierSalesReportFilterSerializer, SalesReportFilterSerializer


def sales_rows(filters, *, queryset=None):
    if queryset is None:
        queryset = Invoice.objects.all()
    queryset = filter_invoices(queryset.filter(payment__order__status=OrderStatus.PAID), filters)
    product = filters.get("product", "").casefold()
    category = filters.get("category")
    rows, categories = [], set()
    for invoice in queryset.order_by("-issued_at", "-pk").iterator(chunk_size=500):
        snapshot = invoice.snapshot
        for index, item in enumerate(snapshot["items"]):
            item_category = item.get("category")
            if item_category:
                categories.add(item_category)
            if product and product not in item["product_name"].casefold() and product != str(item["product_id"]):
                continue
            if category and (item_category or "__unrecorded__") != category:
                continue
            quantity, unit_cost = item["quantity"], item.get("purchase_price")
            cost = quantity * unit_cost if unit_cost is not None else None
            rows.append({
                "id": f"{invoice.pk}-{index}", "invoice_id": invoice.pk, "number": invoice.number,
                "issued_at": invoice.issued_at.isoformat(), "venue": invoice.venue_id,
                "venue_name": snapshot["venue_name"], "product_id": item["product_id"],
                "product_name": item["product_name"], "category": item_category,
                "quantity": quantity, "purchase_value": cost, "sale_value": item["subtotal"],
                "profit": item["subtotal"] - cost if cost is not None else None,
            })
    missing = sum(row["purchase_value"] is None for row in rows)
    total = sum(row["sale_value"] for row in rows)
    cost = sum(row["purchase_value"] for row in rows) if not missing else None
    summary = {"sales": total, "purchase_value": cost, "profit": total - cost if cost is not None else None,
               "quantity": sum(row["quantity"] for row in rows), "transactions": len({row["invoice_id"] for row in rows}),
               "missing_cost_lines": missing, "currency": "COP"}
    return rows, summary, sorted(categories)


def csv_cell(value):
    if value is None:
        return "Not recorded"
    # Protect spreadsheet consumers from formula execution in stored names.
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class SalesReportView(APIView):
    permission_classes = [IsAdministrator]

    def get(self, request):
        serializer = SalesReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        rows, summary, categories = sales_rows(serializer.validated_data)
        if request.query_params.get("export") == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="sales-report.csv"'
            response["Cache-Control"] = "no-store"
            writer = csv.writer(response)
            writer.writerow(["Receipt", "Date (America/Bogota)", "Venue", "Product ID", "Product", "Category", "Quantity", "Purchase value (COP)", "Sale value (COP)", "Profit (COP)"])
            zone = timezone.get_default_timezone()
            for row in rows:
                issued = datetime.fromisoformat(row["issued_at"]).astimezone(zone).isoformat()
                writer.writerow([csv_cell(value) for value in [row["number"], issued, row["venue_name"], row["product_id"], row["product_name"], row["category"], row["quantity"], row["purchase_value"], row["sale_value"], row["profit"]]])
            return response
        if serializer.validated_data.get("export") == "print":
            response = Response({"results": rows, "summary": summary})
            response["Cache-Control"] = "no-store"
            return response
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        response = paginator.get_paginated_response(page)
        response.data["summary"] = summary
        response.data["categories"] = categories
        response["Cache-Control"] = "no-store"
        return response


class IsCashier(BasePermission):
    message = "Only cashiers can access their venue report."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.CASHIER)


class CashierSalesReportView(APIView):
    permission_classes = [IsCashier]

    def get(self, request):
        if request.user.venue_id is None:
            raise PermissionDenied("A venue must be assigned before viewing a sales report.")
        serializer = CashierSalesReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        rows, summary, _ = sales_rows(
            serializer.validated_data, queryset=Invoice.objects.filter(venue_id=request.user.venue_id),
        )
        # An explicit allowlist keeps costs and margins out of every response.
        public_rows = [{key: row[key] for key in (
            "id", "issued_at", "product_id", "product_name", "quantity", "sale_value",
        )} for row in rows]
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(public_rows, request, view=self)
        response = paginator.get_paginated_response(page)
        response.data["summary"] = {key: summary[key] for key in ("sales", "quantity", "transactions", "currency")}
        response["Cache-Control"] = "no-store"
        return response
