# Rôle : définit SettingsConfig, la configuration Django de l'application settings.
# Liens : chargée par Django grâce à apps.settings dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class SettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.settings'
    verbose_name = 'Store Configuration'
