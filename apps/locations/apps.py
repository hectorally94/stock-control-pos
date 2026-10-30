# Rôle : définit LocationsConfig, la configuration Django de l'application locations.
# Liens : chargée par Django grâce à apps.locations dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.locations'
    verbose_name = 'Emplacements'
