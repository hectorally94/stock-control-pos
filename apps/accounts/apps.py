# Rôle : définit AccountsConfig, la configuration Django de l'application accounts.
# Liens : chargée par Django grâce à apps.accounts dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Accounts & Users'
