"""
Vistas del Módulo 9 - Pagos y Facturación.

HU23: Procesar pago en efectivo.
HU24: Procesar pago con tarjeta.
HU25: Generar y consultar la factura.
"""
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.orders.models import Order

from .models import Invoice
from .serializers import InvoiceSerializer, PaymentSerializer
from .services import PaymentError, register_payment


class CanChargeOrders(BasePermission):
    """
    Cobran el Cajero y el Administrador.

    El Mesero registra el pedido pero no maneja la caja.
    """

    message = "Only cashiers and administrators can charge orders."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.CASHIER)
        )


class ChargeOrderView(APIView):
    """
    POST /api/orders/{order_id}/pay/

    Registra el pago del pedido, genera la factura, lo deja en estado PAGADO
    y libera la mesa.
    """

    permission_classes = [CanChargeOrders]

    def post(self, request, order_id):
        order = Order.objects.filter(id=order_id).select_related("venue", "table").first()
        if order is None:
            return Response(
                {"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # El Cajero solo cobra pedidos de su sede asignada.
        if request.user.role != Role.ADMIN and order.venue != request.user.venue:
            return Response(
                {"detail": "You can only charge orders from your own venue."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            invoice = register_payment(
                order=order,
                cashier=request.user,
                payment_method=serializer.validated_data["payment_method"],
                amount_received=serializer.validated_data.get("amount_received"),
                request=request,
            )
        except PaymentError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Facturas emitidas.

    - GET /api/invoices/{id}/  consulta una factura (HU25).

    Las facturas son de solo lectura: el conjunto de vistas no expone
    operaciones de escritura, de modo que no pueden modificarse ni anularse
    desde la API bajo ningún perfil.
    """

    queryset = Invoice.objects.select_related(
        "venue", "order", "order__table", "order__waiter", "cashier"
    ).prefetch_related("order__items__product")
    serializer_class = InvoiceSerializer
    permission_classes = [CanChargeOrders]

    def get_queryset(self):
        queryset = super().get_queryset()

        # El Cajero solo accede a las facturas de su sede asignada.
        if self.request.user.role != Role.ADMIN:
            queryset = queryset.filter(venue=self.request.user.venue)

        return queryset
