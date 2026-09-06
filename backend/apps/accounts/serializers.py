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


class UserUpdateSerializer(UserCreateSerializer):
    """
    Edición de una cuenta existente (HU07).

    Se reutilizan las validaciones de creación (unicidad del nombre de usuario,
    robustez de la contraseña y sede obligatoria según el rol). La contraseña
    es opcional: solo se modifica si se envía.
    """

    password = serializers.CharField(
        write_only=True, min_length=8, max_length=128, required=False
    )

    class Meta(UserCreateSerializer.Meta):
        fields = UserCreateSerializer.Meta.fields

    def validate_role(self, value):
        """
        Un Administrador no puede modificar su propio rol.

        Criterio de aceptación de la HU07: solo otro Administrador puede
        hacerlo, para evitar que el sistema quede sin ninguna cuenta con
        privilegios de administración.
        """
        request = self.context.get("request")
        if (
            request is not None
            and self.instance is not None
            and self.instance.pk == request.user.pk
            and value != self.instance.role
        ):
            raise serializers.ValidationError(
                "You cannot change your own role. Another administrator must do it."
            )
        return value

    def update(self, instance, validated_data):
        """Si se envía contraseña, se almacena cifrada de inmediato."""
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class UserStatusChangeSerializer(serializers.Serializer):
    """
    Confirmación del cambio de estado de una cuenta (HU08).

    La inactivación requiere confirmación explícita del Administrador.
    """

    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm this action.")
        return value
