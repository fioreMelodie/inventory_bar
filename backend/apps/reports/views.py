"""
Vistas del Módulo 10 - Reportes.

HU27: Reporte de ventas del Administrador (todas las sedes).
"""
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.catalog.models import Product
from apps.locations.models import Venue

from .services import build_sales_report, summarize


class CanViewReports(BasePermission):
    """
    Consultan reportes el Administrador y el Cajero.

    El Mesero no accede al módulo: su función es la toma de pedidos.
    """

    message = "Only administrators and cashiers can view sales reports."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.CASHIER)
        )


class SalesReportView(APIView):
    """
    GET /api/reports/sales/

    Reporte de ventas con filtros de fecha, sede, producto y categoría.

    El rango de fechas es obligatorio. El Administrador puede consultar una
    sede concreta o todas consolidadas; el Cajero queda restringido a su sede
    y no recibe valor de compra ni ganancia.
    """

    permission_classes = [CanViewReports]

    def get(self, request):
        date_from = parse_date(request.query_params.get("date_from", ""))
        date_to = parse_date(request.query_params.get("date_to", ""))

        if date_from is None or date_to is None:
            return Response(
                {"detail": "Select a start date and an end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if date_from > date_to:
            return Response(
                {"detail": "The start date cannot be later than the end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        venue = self.resolve_venue(request)
        if isinstance(venue, Response):
            return venue

        product = None
        product_id = request.query_params.get("product")
        if product_id:
            product = Product.objects.filter(id=product_id).first()
            if product is None:
                return Response(
                    {"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND
                )

        rows = build_sales_report(
            date_from=date_from,
            date_to=date_to,
            venue=venue,
            product=product,
            category=request.query_params.get("category"),
        )

        is_admin = request.user.role == Role.ADMIN
        if not is_admin:
            # El margen es información reservada al Administrador (HU28).
            rows = [
                {
                    key: value
                    for key, value in row.items()
                    if key not in ("purchase_value", "profit")
                }
                for row in rows
            ]

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "venue": venue.id if venue else None,
            "venue_name": venue.name if venue else "All venues",
            "results": rows,
            "summary": self.build_summary(rows, is_admin),
        }
        return Response(payload)

    def resolve_venue(self, request):
        """
        Determina la sede del reporte.

        El Cajero queda fijado a su sede asignada; el Administrador elige, y
        sin selección obtiene el consolidado de todas.
        """
        if request.user.role != Role.ADMIN:
            if request.user.venue is None:
                return Response(
                    {"detail": "Your account has no venue assigned."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return request.user.venue

        venue_id = request.query_params.get("venue")
        if not venue_id:
            return None

        venue = Venue.objects.filter(id=venue_id).first()
        if venue is None:
            return Response(
                {"detail": "Venue not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return venue

    def build_summary(self, rows, is_admin):
        """Totales del reporte, sin margen cuando el rol no debe verlo."""
        if is_admin:
            return summarize(rows)

        return {
            "quantity": sum(row["quantity"] for row in rows),
            "sale_value": sum(row["sale_value"] for row in rows),
        }
