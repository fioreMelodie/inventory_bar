"""Rutas del Módulo 9 - Pagos y Facturación."""
from django.urls import path

from .views import ChargeOrderView

app_name = "billing"

urlpatterns = [
    path("orders/<int:order_id>/pay/", ChargeOrderView.as_view(), name="charge-order"),
]
