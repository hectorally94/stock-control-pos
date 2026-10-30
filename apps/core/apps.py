# Rôle : définit CoreConfig, la configuration Django de l'application core.
# Liens : chargée par Django grâce à apps.core dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'
