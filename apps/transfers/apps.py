# Rôle : définit TransfersConfig, la configuration Django de l'application transfers.
# Liens : chargée par Django grâce à apps.transfers dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class TransfersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.transfers'
    verbose_name = 'Transferts'
