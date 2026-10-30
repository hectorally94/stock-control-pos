from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customers'
    verbose_name = 'Customers & Credits'
    
    def ready(self):
        """Import signal handlers when app is ready"""
        import apps.customers.signals