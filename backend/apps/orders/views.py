"""
Vistas del Módulo 8 - Gestión de Pedidos.

HU19: Crear pedido (Mesero).
HU16: Descuento automático de stock y reintegro al cancelar.
"""
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.audit.models import EventType
from apps.audit.services import record_event
from apps.inventory.services import restore_for_order
from apps.tables.models import TableStatus

from .models import Order, OrderStatus
from .serializers import OrderCreateSerializer, OrderSerializer


class CanTakeOrders(BasePermission):
    """
    Toman pedidos el Mesero y el Administrador.

    El Administrador puede asumir el rol de mesero cuando la operación lo
    requiera (propuesta comercial V1.1, sección 02).
    """

    message = "Only waiters and administrators can take orders."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role in (Role.WAITER, Role.ADMIN)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Pedidos asociados a mesas.

    - POST /api/orders/  abre un pedido sobre una mesa libre (HU19).
    - GET  /api/orders/  lista los pedidos de la sede.

    Los pedidos no se eliminan: quedan registrados de forma permanente.
    """

    queryset = Order.objects.select_related("venue", "table", "waiter")
    permission_classes = [CanTakeOrders]

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Cajero y Mesero solo acceden a los pedidos de su sede asignada.
        if self.request.user.role != Role.ADMIN:
            queryset = queryset.filter(venue=self.request.user.venue)
        else:
            venue_id = self.request.query_params.get("venue")
            if venue_id:
                queryset = queryset.filter(venue_id=venue_id)

        order_status = self.request.query_params.get("status")
        if order_status:
            queryset = queryset.filter(status=order_status)

        table_id = self.request.query_params.get("table")
        if table_id:
            queryset = queryset.filter(table_id=table_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """Abre el pedido y marca la mesa como ocupada."""
        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        table = serializer.validated_data["table"]

        with transaction.atomic():
            order = Order.objects.create(
                venue=table.venue,
                table=table,
                waiter=request.user,
                status=OrderStatus.OPEN,
            )
            table.status = TableStatus.OCCUPIED
            table.save(update_fields=["status", "updated_at"])

        record_event(
            event_type=EventType.ORDER_OPENED,
            username=request.user.username,
            user=request.user,
            entity="Order",
            entity_id=order.id,
            description=(
                f"Apertura del pedido {order.id} en la mesa '{table.identifier}' "
                f"de la sede '{table.venue.name}'."
            ),
            request=request,
        )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """
        POST /api/orders/{id}/cancel/

        Cancela un pedido ABIERTO, reintegra al inventario las unidades que
        había descontado y libera la mesa.

        El pedido no se elimina: queda registrado en estado CANCELADO, porque
        el histórico de pedidos es permanente. Un pedido ya enviado a caja no
        puede cancelarse.
        """
        order = self.get_object()

        if not order.is_open:
            return Response(
                {"detail": "Only open orders can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            restore_for_order(order=order, performed_by=request.user, request=request)

            order.status = OrderStatus.CANCELLED
            order.save(update_fields=["status"])

            table = order.table
            table.status = TableStatus.FREE
            table.save(update_fields=["status", "updated_at"])

        record_event(
            event_type=EventType.ORDER_CANCELLED,
            username=request.user.username,
            user=request.user,
            entity="Order",
            entity_id=order.id,
            description=(
                f"Cancelación del pedido {order.id} de la mesa "
                f"'{table.identifier}'. El stock descontado fue reintegrado."
            ),
            request=request,
        )

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
