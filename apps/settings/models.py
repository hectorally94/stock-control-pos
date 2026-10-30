from django.db import models


class StoreSetting(models.Model):
    """Store configuration settings"""
    
    key = models.CharField(max_length=100, unique=True, verbose_name='Key')
    value = models.TextField(blank=True, null=True, verbose_name='Value')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        db_table = 'store_settings'
        verbose_name = 'Store Setting'
        verbose_name_plural = 'Store Settings'
        indexes = [
            models.Index(fields=['key'], name='idx_store_settings_key'),
        ]
    
    # Rôle : affiche le paramètre sous la forme « clé: valeur ».
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    # Rôle : lit la valeur d'une clé et renvoie la valeur par défaut si la clé n'existe pas.
    # Liens : appelée par apps/customers/signals.py, apps/pos/utils/receipt_generator.py, api/v1/views/settings.py.
    @classmethod
    def get_setting(cls, key, default=None):
        """Helper method to retrieve a setting value"""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
    
    # Rôle : crée la clé ou met à jour sa valeur, puis renvoie le StoreSetting.
    # Liens : appelée par l'action set_setting de api/v1/views/settings.py.
    @classmethod
    def set_setting(cls, key, value):
        """Helper method to set a setting value"""
        setting, created = cls.objects.update_or_create(key=key, defaults={'value': value})
        return setting
