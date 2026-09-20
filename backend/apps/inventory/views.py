"""
Vistas del Módulo 6 - Gestión de Inventario.

HU14: Registrar entrada de mercancía al inventario.
HU15: Consultar stock disponible por sede.
"""
from django.db.models import OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.catalog.models import Product
from apps.locations.models import Venue

from .models import Stock
from .serializers import StockEntrySerializer, StockSerializer, VenueStockSerializer
from .services import register_entry


class CanManageInventory(BasePermission):
    """
    Gestionan inventario el Cajero (en su sede) y el Administrador (en todas).

    El Mesero no registra entradas ni ajusta existencias.
    """

    message = "Only cashiers and administrators can manage inventory."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.CASHIER)
        )


class StockEntryView(APIView):
    """
    POST /api/inventory/entries/

    Registra la entrada de mercancía y suma la cantidad recibida al stock del
    producto en la sede.
    """

    permission_classes = [CanManageInventory]

    def post(self, request):
        serializer = StockEntrySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        stock, _ = register_entry(
            venue=serializer.validated_data["venue"],
            product=serializer.validated_data["product"],
            quantity=serializer.validated_data["quantity"],
            performed_by=request.user,
            request=request,
        )

        return Response(StockSerializer(stock).data, status=status.HTTP_201_CREATED)


class VenueStockView(APIView):
    """
    GET /api/inventory/stock/

    Devuelve el stock actual de cada producto del catálogo en una sede.

    El Administrador puede consultar cualquier sede mediante el parámetro
    `venue`; el Cajero solo accede al inventario de su sede asignada. Se
    admiten además los filtros `search` (nombre de producto) y `category`.
    """

    permission_classes = [CanManageInventory]

    def get(self, request):
        venue = self.resolve_venue(request)
        if isinstance(venue, Response):
            return venue

        products = Product.objects.filter(is_active=True)

        search = request.query_params.get("search")
        if search:
            products = products.filter(name__icontains=search.strip())

        category = request.query_params.get("category")
        if category:
            products = products.filter(category__iexact=category.strip())

        # Un producto sin movimientos en la sede no tiene registro de Stock:
        # se informa con cantidad cero en lugar de omitirlo del listado.
        products = products.annotate(
            quantity=Coalesce(
                Subquery(
                    Stock.objects.filter(
                        venue=venue, product=OuterRef("pk")
                    ).values("quantity")[:1]
                ),
                Value(0),
            )
        ).order_by("name")

        return Response(
            {
                "venue": venue.id,
                "venue_name": venue.name,
                "results": VenueStockSerializer(products, many=True).data,
            }
        )

    def resolve_venue(self, request):
        """Determina la sede consultada aplicando el alcance del rol."""
        requested = request.query_params.get("venue")

        if request.user.role == Role.ADMIN:
            if requested:
                venue = Venue.objects.filter(id=requested).first()
                if venue is None:
                    return Response(
                        {"detail": "Venue not found."}, status=status.HTTP_404_NOT_FOUND
                    )
                return venue

            venue = request.user.venue or Venue.objects.filter(is_active=True).first()
            if venue is None:
                return Response(
                    {"detail": "There are no venues registered yet."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return venue

        # El Cajero solo accede al inventario de su sede, aunque pida otra.
        if request.user.venue is None:
            return Response(
                {"detail": "Your account has no venue assigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return request.user.venue
