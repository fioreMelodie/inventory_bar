"""Permisos por rol del sistema."""
from rest_framework.permissions import BasePermission

from .models import Role


class IsAdministrator(BasePermission):
    """
    Restringe el acceso al rol Administrador.

    La parametrización de sedes, usuarios, mesas y productos es exclusiva del
    Administrador (propuesta comercial V1.1, sección 3.2.1.1).
    """

    message = "Only administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == Role.ADMIN
        )
