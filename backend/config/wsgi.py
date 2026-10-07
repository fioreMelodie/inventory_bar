"""Configuración WSGI para el proyecto Bar Inventory APP."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Vercel (@vercel/python) busca una variable llamada "app".
app = application
