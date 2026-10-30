from django.apps import AppConfig


class PosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pos'
    verbose_name = 'Point of Sale'
    
    # Rôle : importe les signaux de la caisse pour que leurs @receiver soient enregistrés au démarrage.
    # Liens : appelée par Django (app apps.pos de stock_control/settings.py) ; charge apps/pos/signals.py.
    def ready(self):
        """Import signal handlers when app is ready"""
        import apps.pos.signals