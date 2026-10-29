"""Rutas del Módulo 11 - Auditoría y Trazabilidad."""
from rest_framework.routers import DefaultRouter

from .views import AuditEventViewSet

app_name = "audit"

router = DefaultRouter()
router.register("audit/events", AuditEventViewSet, basename="audit-event")

urlpatterns = router.urls
