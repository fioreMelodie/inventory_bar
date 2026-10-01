"""Rutas del Módulo 1 - Autenticación y Sesión."""
from django.urls import path

from .views import (
    CurrentUserView,
    LoginView,
    LogoutView,
    SessionExpireView,
    SessionTokenRefreshView,
)

app_name = "authentication"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("refresh/", SessionTokenRefreshView.as_view(), name="token-refresh"),
    path("session/expire/", SessionExpireView.as_view(), name="session-expire"),
]
