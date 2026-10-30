from django.contrib import admin
from .models import Enterprise


@admin.register(Enterprise)
class EnterpriseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'phone', 'email', 'currency', 'is_active', 'created_at']
    list_filter = ['is_active', 'currency', 'created_at']
    search_fields = ['name', 'code', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['name']

    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'is_active')
        }),
        ('Contact', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Business Info', {
            'fields': ('tax_id', 'currency', 'logo')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    # Rôle : renseigne created_by avec l'utilisateur connecté à la création d'une entreprise, pas à la modification.
    # Liens : appelée par l'admin Django à l'enregistrement ; écrit sur Enterprise (apps/core/models.py).
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
