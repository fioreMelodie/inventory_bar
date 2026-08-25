"""Enrutamiento principal de la API - Bar Inventory APP."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    """Endpoint de verificación de disponibilidad del servicio."""
    return JsonResponse({"status": "ok", "service": "Bar Inventory APP"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("apps.authentication.urls")),
]
