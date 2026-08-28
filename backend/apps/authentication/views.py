"""
Vistas del Módulo 1 - Autenticación y Sesión.

HU01: Inicio de sesión con credenciales.
"""
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.audit.models import EventType
from apps.audit.services import get_client_ip, record_event

from .authentication import close_session_by_inactivity
from .models import UserSession
from .serializers import (
    AuthenticatedUserSerializer,
    LoginSerializer,
    LogoutSerializer,
    SessionTokenSerializer,
)
from .services import get_lockout_remaining, register_attempt
from .session_services import close_session

# Los mensajes devueltos por la API se muestran directamente al usuario, por lo
# que están en inglés (requisito no funcional: todo el frontend en inglés).
INVALID_CREDENTIALS_MESSAGE = "Invalid username or password."


class LoginView(APIView):
    """
    POST /api/auth/login/

    Valida las credenciales, crea la sesión y devuelve los tokens de acceso.

    Criterios de aceptación aplicados (HU01):
      - Solo usuarios con estado activo=1 pueden iniciar sesión.
      - El mensaje de error no indica cuál campo es incorrecto.
      - Tras 3 intentos fallidos consecutivos el acceso se bloquea 5 minutos.
      - Se registra el intento en el log de auditoría.
      - La sesión registra usuario, rol, fecha y hora de ingreso.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        ip_address = get_client_ip(request)

        # 1. Verificar bloqueo por intentos fallidos antes de validar nada más.
        remaining = get_lockout_remaining(username)
        if remaining > 0:
            minutes = max(1, -(-remaining // 60))  # redondeo hacia arriba
            record_event(
                event_type=EventType.LOGIN_BLOCKED,
                username=username,
                description=f"Acceso bloqueado. Faltan {remaining} segundos para el desbloqueo.",
                request=request,
            )
            return Response(
                {
                    "detail": (
                        f"Account temporarily locked after 3 failed attempts. "
                        f"Try again in {minutes} minute{'s' if minutes != 1 else ''}."
                    ),
                    "locked": True,
                    "retry_after_seconds": remaining,
                },
                status=status.HTTP_423_LOCKED,
            )

        # 2. Validar credenciales. authenticate() devuelve None tanto si el
        #    usuario no existe como si la contraseña es incorrecta o la cuenta
        #    está inactiva: el mensaje de error es el mismo en los tres casos.
        user = authenticate(request, username=username, password=password)

        if user is None:
            register_attempt(username, successful=False, ip_address=ip_address)

            # Se identifica la causa real solo para el log de auditoría, nunca
            # para la respuesta al usuario.
            existing = User.objects.filter(username=username).first()
            if existing is None:
                motivo = "El usuario no existe."
            elif not existing.is_active:
                motivo = "La cuenta se encuentra inactiva."
            else:
                motivo = "Contraseña incorrecta."

            record_event(
                event_type=EventType.LOGIN_FAILED,
                username=username,
                user=existing,
                description=motivo,
                request=request,
            )
            return Response(
                {"detail": INVALID_CREDENTIALS_MESSAGE},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 3. Credenciales válidas: registrar intento, sesión y evento.
        register_attempt(username, successful=True, ip_address=ip_address)

        session = UserSession.objects.create(
            user=user,
            role=user.role,
            venue=user.venue,
            ip_address=ip_address,
        )

        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session.id
        refresh["role"] = user.role

        record_event(
            event_type=EventType.LOGIN_SUCCESS,
            username=user.username,
            user=user,
            entity="UserSession",
            entity_id=session.id,
            description=f"Inicio de sesión con rol {user.get_role_display()}.",
            request=request,
        )

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": AuthenticatedUserSerializer(user).data,
                "session_id": session.id,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    """
    GET /api/auth/me/

    Devuelve el usuario de la sesión activa. El frontend lo usa para restaurar
    la sesión al recargar la página y para verificar que el token sigue siendo
    válido en el servidor.
    """

    def get(self, request):
        return Response(AuthenticatedUserSerializer(request.user).data)


class SessionExpireView(APIView):
    """
    POST /api/auth/session/expire/

    HU02: cierre automático de sesión por inactividad.

    El frontend invoca este endpoint cuando su temporizador local alcanza los
    3 minutos sin interacción. Se acepta el refresh token en el cuerpo porque
    para ese momento el access token puede haber expirado.

    El servidor invalida la sesión de forma definitiva: cierra el registro de
    sesión y revoca el refresh token, de modo que la invalidación no depende
    del frontend.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = SessionTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError:
            # Un token ya expirado o revocado equivale a una sesión cerrada.
            return Response(
                {"detail": "Session already closed."}, status=status.HTTP_200_OK
            )

        session = UserSession.objects.filter(id=token.get("session_id")).first()
        if session is not None and session.is_active:
            close_session_by_inactivity(session, request=request)

        # Revocar el refresh token impide obtener nuevos access tokens.
        try:
            token.blacklist()
        except AttributeError:  # pragma: no cover - blacklist siempre habilitado
            pass

        return Response(
            {"detail": "Session closed due to inactivity."}, status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/

    HU03: cierre de sesión manual y manejo de pérdida de conexión.

    El motivo del cierre se recibe en el cuerpo y determina el evento que queda
    en el log de auditoría:
      - MANUAL: el usuario pulsó "Sign out".
      - DISCONNECTION: el frontend detectó la pérdida de conexión.

    El cierre no elimina datos no guardados: los pedidos activos permanecen en
    la base de datos.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
        except TokenError:
            return Response({"detail": "Session already closed."}, status=status.HTTP_200_OK)

        session = UserSession.objects.filter(id=token.get("session_id")).first()
        if session is not None:
            close_session(session, reason, request=request)

        try:
            token.blacklist()
        except AttributeError:  # pragma: no cover - blacklist siempre habilitado
            pass

        return Response({"detail": "Signed out successfully."}, status=status.HTTP_200_OK)
