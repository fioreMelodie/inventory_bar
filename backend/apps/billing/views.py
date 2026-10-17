"""
Vistas del Módulo 9 - Pagos y Facturación.

HU23: Procesar pago en efectivo.
HU24: Procesar pago con tarjeta.
HU25: Generar y consultar la factura.
HU26: Consultar el historial de facturas.
"""
from django.utils.dateparse import parse_date
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


class InvoiceViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Facturas emitidas.

    - GET /api/invoices/       historial con filtros (HU26).
    - GET /api/invoices/{id}/  consulta una factura (HU25).

    El historial admite los filtros `date_from`, `date_to`, `number` y
    `venue`, combinables entre sí. Cubre desde el inicio del sistema: las
    facturas nunca se eliminan.

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
        else:
            venue_id = self.request.query_params.get("venue")
            if venue_id:
                queryset = queryset.filter(venue_id=venue_id)

        if self.action != "list":
            return queryset

        # Los filtros son aditivos: cada uno reduce el conjunto de resultados.
        date_from = parse_date(self.request.query_params.get("date_from", ""))
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = parse_date(self.request.query_params.get("date_to", ""))
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        number = self.request.query_params.get("number")
        if number:
            queryset = queryset.filter(number__icontains=number.strip())

        return queryset

    def list(self, request, *args, **kwargs):
        """Valida el rango de fechas antes de construir el listado."""
        date_from = parse_date(request.query_params.get("date_from", ""))
        date_to = parse_date(request.query_params.get("date_to", ""))

        if date_from and date_to and date_from > date_to:
            return Response(
                {"detail": "The start date cannot be later than the end date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().list(request, *args, **kwargs)
