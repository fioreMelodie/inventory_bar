"""Rutas del Módulo 1 - Autenticación y Sesión."""
from django.urls import path

from .views import CurrentUserView, LoginView

app_name = "authentication"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
]
