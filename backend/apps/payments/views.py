from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Role

from .models import Invoice
from .filters import filter_invoices
from .serializers import (CardPaymentSerializer, CashPaymentSerializer, InvoiceFilterSerializer,
                          InvoiceListSerializer, InvoiceSerializer, PaymentSerializer)
from .services import PaymentConflict, pay_card, pay_cash


class CanProcessPayments(BasePermission):
    message = "Only cashiers and administrators can access payments."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role in (Role.ADMIN, Role.CASHIER)
        )


class CashPaymentView(APIView):
    permission_classes = [CanProcessPayments]
    serializer_class = CashPaymentSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            payment, created = self.record_payment(data, request)
        except IntegrityError:
            raise PaymentConflict("A payment was recorded concurrently. Reload the order before trying again.")
        return Response(
            {"payment": PaymentSerializer(payment).data, "invoice": InvoiceSerializer(payment.invoice).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def record_payment(self, data, request):
        return pay_cash(
            order_id=data["order"], received_amount=data["received_amount"],
            expected_total=data["expected_total"], idempotency_key=data["idempotency_key"],
            cashier=request.user, request=request,
        )


class CardPaymentView(CashPaymentView):
    serializer_class = CardPaymentSerializer

    def record_payment(self, data, request):
        return pay_card(
            order_id=data["order"], method=data["method"], approval_reference=data["approval_reference"],
            terminal_approved=data["terminal_approved"], expected_total=data["expected_total"],
            idempotency_key=data["idempotency_key"], cashier=request.user, request=request,
        )


class InvoiceScopeMixin:
    permission_classes = [CanProcessPayments]

    def get_queryset(self):
        queryset = Invoice.objects.order_by("-issued_at", "-pk")
        if self.request.user.role != Role.ADMIN:
            queryset = queryset.filter(venue=self.request.user.venue)
        return queryset


class InvoiceListView(InvoiceScopeMixin, generics.ListAPIView):
    serializer_class = InvoiceListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        filters = InvoiceFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return filter_invoices(queryset, filters.validated_data)


class InvoiceDetailView(InvoiceScopeMixin, generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
