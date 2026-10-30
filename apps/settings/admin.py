# Rôle : configure StoreSetting (paires clé et valeur) dans l'administration Django.
# Liens : modèle de apps/settings/models.py ; pages servies sous admin/ (stock_control/urls.py).
from django.contrib import admin
from .models import StoreSetting


@admin.register(StoreSetting)
class StoreSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at')
    search_fields = ('key', 'value')
    readonly_fields = ('updated_at',)
    ordering = ('key',)
