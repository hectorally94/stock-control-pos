# Rôle : définit AccountingConfig, la configuration Django de l'application accounting.
# Liens : chargée par Django grâce à apps.accounting dans INSTALLED_APPS (stock_control/settings.py).
from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounting'
    verbose_name = 'Accounting & Expenses'
