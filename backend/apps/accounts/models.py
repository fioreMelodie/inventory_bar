"""
Módulo de Administración de Usuarios.

Modelo de usuario propio del sistema. No se usa el modelo por defecto de Django
porque cada cuenta requiere un rol operativo y una sede asignada que determinan
el alcance de la información a la que accede.

Regla de negocio: no existe autoregistro. Únicamente el Administrador crea
cuentas (propuesta comercial V1.1, sección 3.1).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Role(models.TextChoices):
    """
    Roles operativos del sistema.

    Los valores almacenados están en inglés para mantener coherencia con la
    interfaz de usuario; las etiquetas en español se usan en el panel de
    administración y la documentación.
    """

    ADMIN = "ADMIN", "Administrador"
    CASHIER = "CASHIER", "Cajero"
    WAITER = "WAITER", "Mesero"


class UserManager(BaseUserManager):
    """Gestor del modelo de usuario."""

    use_in_migrations = True

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("El nombre de usuario es obligatorio.")
        extra_fields.setdefault("is_active", True)
        user = self.model(username=username, **extra_fields)
        # set_password aplica el algoritmo de hashing configurado en Django
        # (PBKDF2). La contraseña nunca se almacena en texto plano.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Cuenta de acceso al sistema, con rol operativo asignado."""

    username = models.CharField(
        "nombre de usuario",
        max_length=150,
        unique=True,
        help_text="Debe ser único en todo el sistema.",
    )
    full_name = models.CharField("nombre completo", max_length=200)
    role = models.CharField("rol", max_length=20, choices=Role.choices)

    # El campo activo controla el acceso: un usuario inactivo no puede
    # autenticarse, pero su historial de actividad se conserva íntegro.
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al panel de administración", default=False)

    created_at = models.DateTimeField("fecha de creación", auto_now_add=True)
    updated_at = models.DateTimeField("última modificación", auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.username})"

    @property
    def is_admin(self):
        """El Administrador accede a la información de todas las sedes."""
        return self.role == Role.ADMIN
