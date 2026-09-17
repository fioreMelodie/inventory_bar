"""
Vistas del Módulo 6 - Gestión de Inventario.

HU14: Registrar entrada de mercancía al inventario.
"""
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role

from .serializers import StockEntrySerializer, StockSerializer
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
