"""Rutas del Módulo 6 - Gestión de Inventario."""
from django.urls import path

from .views import StockEntryView

app_name = "inventory"

urlpatterns = [
    path("inventory/entries/", StockEntryView.as_view(), name="stock-entry"),
]
