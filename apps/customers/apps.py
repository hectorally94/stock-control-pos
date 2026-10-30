from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'
    verbose_name = 'Customers & Credits'
    
    # Rôle : importe apps/customers/signals.py pour enregistrer ses récepteurs au démarrage.
    # Liens : appelée par Django au chargement de l'app déclarée dans stock_control/settings.py.
    def ready(self):
        """Import signal handlers when app is ready"""
        import apps.customers.signals