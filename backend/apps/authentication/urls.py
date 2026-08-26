"""Rutas del Módulo 1 - Autenticación y Sesión."""
from django.urls import path

from .views import CurrentUserView, LoginView, SessionExpireView

app_name = "authentication"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("session/expire/", SessionExpireView.as_view(), name="session-expire"),
]
