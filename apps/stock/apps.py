# Rôle : définit StockConfig, la configuration Django de l'application stock.
# Liens : chargée par Django grâce à apps.stock dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class StockConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.stock'
    verbose_name = 'Stock Management'
