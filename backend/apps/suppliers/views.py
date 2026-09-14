"""
Vistas del Módulo 5 - Gestión de Proveedores.

HU12: Registrar proveedor.
"""
from rest_framework import viewsets

from apps.accounts.permissions import IsAdministrator
from apps.audit.models import EventType
from apps.audit.services import record_event

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    """
    Directorio de proveedores.

    - POST   /api/suppliers/       registra un proveedor (HU12).
    - GET    /api/suppliers/       lista el directorio.
    - PATCH  /api/suppliers/{id}/  actualiza sus datos de contacto.
    - DELETE /api/suppliers/{id}/  elimina el registro.

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
