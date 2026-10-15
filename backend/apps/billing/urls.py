"""Rutas del Módulo 9 - Pagos y Facturación."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChargeOrderView, InvoiceViewSet

app_name = "billing"

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("orders/<int:order_id>/pay/", ChargeOrderView.as_view(), name="charge-order"),
] + router.urls
