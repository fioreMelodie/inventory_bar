"""Rutas del Módulo 5 - Gestión de Proveedores."""
from rest_framework.routers import DefaultRouter

from .views import SupplierViewSet

app_name = "suppliers"

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="supplier")

urlpatterns = router.urls
