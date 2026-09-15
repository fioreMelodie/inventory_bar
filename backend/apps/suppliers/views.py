"""
Vistas del Módulo 5 - Gestión de Proveedores.

HU12: Registrar proveedor.
"""
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event
from apps.catalog.models import Product
from apps.catalog.serializers import ProductSerializer

from .models import Supplier
from .serializers import SupplierProductsSerializer, SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    """
    Directorio de proveedores.

    - POST   /api/suppliers/       registra un proveedor (HU12).
    - GET    /api/suppliers/       lista el directorio.
    - PATCH  /api/suppliers/{id}/  actualiza sus datos de contacto.
    - DELETE /api/suppliers/{id}/  elimina el registro.
    - GET    /api/suppliers/{id}/products/  productos que suministra (HU13).
    - PUT    /api/suppliers/{id}/products/  define esa lista (HU13).

    Solo el Administrador puede crear, editar o eliminar proveedores. El
    módulo es informativo: no genera transacciones ni afecta el inventario.
    """

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdministrator]

    def get_queryset(self):
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search.strip())

        return queryset

    @action(detail=True, methods=["get", "put"])
    def products(self, request, pk=None):
        """
        Productos asociados al proveedor.

        GET devuelve los productos que suministra. PUT reemplaza la lista
        completa: los productos que se omitan quedan desvinculados. La
        asociación es solo informativa y no genera órdenes de compra.
        """
        supplier = self.get_object()

        if request.method == "GET":
            serializer = ProductSerializer(
                supplier.products.all(), many=True, context=self.get_serializer_context()
            )
            return Response(serializer.data)

        serializer = SupplierProductsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data["products"]

        previous = set(supplier.products.values_list("id", flat=True))
        selected_ids = {product.id for product in selected}

        with transaction.atomic():
            # Un producto tiene un solo proveedor principal: asignarlo a este
            # proveedor lo retira automáticamente del anterior.
            Product.objects.filter(id__in=selected_ids).update(supplier=supplier)
            # Los productos que ya no están en la lista quedan sin proveedor.
            Product.objects.filter(supplier=supplier).exclude(
                id__in=selected_ids
            ).update(supplier=None)

        added = selected_ids - previous
        removed = previous - selected_ids
        record_event(
            event_type=EventType.SUPPLIER_PRODUCTS_LINKED,
            username=request.user.username,
            user=request.user,
            entity="Supplier",
            entity_id=supplier.id,
            description=(
                f"Asociación de productos al proveedor '{supplier.name}'. "
                f"Asociados: {len(added)}; desvinculados: {len(removed)}; "
                f"total actual: {len(selected_ids)}."
            ),
            request=request,
        )

        productos = ProductSerializer(
            supplier.products.all(), many=True, context=self.get_serializer_context()
        )
        return Response(productos.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        supplier = serializer.save()
        record_event(
            event_type=EventType.SUPPLIER_CREATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Supplier",
            entity_id=supplier.id,
            description=f"Registro del proveedor '{supplier.name}'.",
            request=self.request,
        )

    def perform_update(self, serializer):
        supplier = serializer.instance
        tracked_fields = ("name", "phone", "email")
        previous = {field: getattr(supplier, field) for field in tracked_fields}

        supplier = serializer.save()

        changes = [
            f"{field}: '{previous[field]}' -> '{getattr(supplier, field)}'"
            for field in tracked_fields
            if previous[field] != getattr(supplier, field)
        ]
        record_event(
            event_type=EventType.SUPPLIER_UPDATED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Supplier",
            entity_id=supplier.id,
            description=(
                f"Edición del proveedor '{supplier.name}'. " + "; ".join(changes)
                if changes
                else f"Edición del proveedor '{supplier.name}' sin cambios efectivos."
            ),
            request=self.request,
        )

    def perform_destroy(self, instance):
        # Se deja constancia antes de eliminar, porque el registro de auditoría
        # debe sobrevivir a la desaparición del proveedor.
        record_event(
            event_type=EventType.SUPPLIER_DELETED,
            username=self.request.user.username,
            user=self.request.user,
            entity="Supplier",
            entity_id=instance.id,
            description=f"Eliminación del proveedor '{instance.name}'.",
            request=self.request,
        )
        instance.delete()
