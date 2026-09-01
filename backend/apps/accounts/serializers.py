"""Serializadores del Módulo 3 - Administración de Usuarios."""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.locations.models import Venue

from .models import Role, User


class UserSerializer(serializers.ModelSerializer):
    """Representación de un usuario para consulta."""

    venue_name = serializers.CharField(source="venue.name", default=None, read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "full_name",
            "role",
            "role_label",
            "venue",
            "venue_name",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Creación de una cuenta de usuario (HU06).

    El Administrador define nombre completo, usuario, contraseña temporal, rol
    y sede asignada. No existe autoregistro.
    """

    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    venue = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ("id", "username", "full_name", "role", "venue", "password")
        extra_kwargs = {
            "username": {
                "error_messages": {
                    "unique": "This username is already taken.",
                    "blank": "Username is required.",
                    "required": "Username is required.",
                }
            },
            "full_name": {
                "error_messages": {
                    "blank": "Full name is required.",
                    "required": "Full name is required.",
                }
            },
            "role": {
                "error_messages": {
                    "invalid_choice": "Select a valid role.",
                    "required": "Role is required.",
                }
            },
        }

    def validate_username(self, value):
        """El nombre de usuario debe ser único en todo el sistema."""
        username = value.strip()
        if not username:
            raise serializers.ValidationError("Username is required.")

        duplicates = User.objects.filter(username__iexact=username)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("This username is already taken.")

        return username

    def validate_password(self, value):
        """Aplica las reglas de robustez de contraseña configuradas (OWASP)."""
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate(self, attrs):
        """
        La sede es obligatoria para Cajero y Mesero.

        El alcance de la información de estos roles se limita a su sede
        asignada, por lo que una cuenta sin sede no podría operar. El
        Administrador accede a todas las sedes y puede quedar sin sede fija.
        """
        role = attrs.get("role", getattr(self.instance, "role", None))
        venue = attrs.get("venue", getattr(self.instance, "venue", None))

        if role in (Role.CASHIER, Role.WAITER) and venue is None:
            raise serializers.ValidationError(
                {"venue": "Cashiers and waiters must be assigned to a venue."}
            )

        return attrs

    def create(self, validated_data):
        """La contraseña se almacena cifrada; nunca en texto plano."""
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)
