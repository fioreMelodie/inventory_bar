"""Rutas del Módulo 4 - Catálogo de Productos."""
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet

app_name = "catalog"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")

urlpatterns = router.urls
