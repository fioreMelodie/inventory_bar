"""Serializadores del módulo de Autenticación y Sesión."""
from rest_framework import serializers

from apps.accounts.models import User


class LoginSerializer(serializers.Serializer):
    """Credenciales de acceso enviadas desde el formulario de login."""

    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)


class AuthenticatedUserSerializer(serializers.ModelSerializer):
    """Datos del usuario que el frontend necesita tras iniciar sesión."""

    class Meta:
        model = User
        fields = ("id", "username", "full_name", "role")
        read_only_fields = fields


class SessionTokenSerializer(serializers.Serializer):
    """Refresh token asociado a la sesión que se desea cerrar."""

    refresh = serializers.CharField()
