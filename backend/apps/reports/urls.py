"""Rutas del Módulo 10 - Reportes."""
from django.urls import path

from .views import SalesReportView

app_name = "reports"

urlpatterns = [
    path("reports/sales/", SalesReportView.as_view(), name="sales"),
]
