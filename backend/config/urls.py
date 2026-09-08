"""Enrutamiento principal de la API - Bar Inventory APP."""
from django.conf import settings
from django.conf.urls.static import static
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
    path("api/", include("apps.locations.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.catalog.urls")),
]

# En desarrollo, Django sirve las imágenes de producto cargadas por el usuario.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
