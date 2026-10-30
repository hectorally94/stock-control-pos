# Rôle : définit ProductsConfig, la configuration Django de l'application products.
# Liens : chargée par Django grâce à apps.products dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.products'
    verbose_name = 'Products & Categories'
