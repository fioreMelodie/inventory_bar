"""Rutas del Módulo 2 - Administración de Sedes."""
from rest_framework.routers import DefaultRouter

from .views import VenueViewSet

app_name = "locations"

router = DefaultRouter()
router.register("venues", VenueViewSet, basename="venue")

urlpatterns = router.urls
