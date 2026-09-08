"""
Vistas del Módulo 4 - Catálogo de Productos.

HU09: Crear producto en el catálogo.
"""
from rest_framework import mixins, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    Productos del catálogo global.

    - POST /api/products/  crea un producto (solo Administrador).
    - GET  /api/products/  lista los productos del catálogo.

    El catálogo es compartido por todas las sedes: los atributos y los precios
    son iguales en todas ellas.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # MultiPart y Form permiten la carga opcional de la imagen del producto.
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        # Consultar el catálogo lo puede hacer cualquier usuario autenticado;
        # crearlo y modificarlo, solo el Administrador.
        if self.action in ("list", "retrieve"):
            return super().get_permissions()
        return [IsAdministrator()]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action not in ("list",):
            return queryset

        # Solo se muestran productos activos, salvo que el Administrador pida
        # explícitamente ver también los inactivos.
        if self.request.query_params.get("include_inactive") == "true":
            return queryset
        return queryset.filter(is_active=True)

    def perform_create(self, serializer):
        product = serializer.save()
        record_event(
            event_type=EventType.PRODUCT_CREATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Product",
            entity_id=product.id,
            description=(
                f"Creación del producto '{product.name}' "
                f"({product.product_type} / {product.category}) "
                f"con valor de venta {product.sale_price}."
            ),
            request=self.request,
        )
