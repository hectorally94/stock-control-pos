from django.contrib import admin
from .models import Transfer, TransferItem


class TransferItemInline(admin.TabularInline):
    model = TransferItem
    extra = 1
    raw_id_fields = ['product']
    fields = ['product', 'quantity', 'received_quantity', 'unit_cost', 'notes']


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['reference', 'source_location', 'destination_location', 'status', 'total_items', 'created_at', 'created_by']
    list_filter = ['enterprise', 'status', 'source_location', 'destination_location', 'created_at']
    search_fields = ['reference', 'notes']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'sent_at', 'received_at', 'cancelled_at',
                      'created_by', 'sent_by', 'received_by', 'cancelled_by']
    raw_id_fields = ['source_location', 'destination_location']
    date_hierarchy = 'created_at'
    inlines = [TransferItemInline]

    fieldsets = (
        (None, {
            'fields': ('enterprise', 'reference', 'status')
        }),
        ('Emplacements', {
            'fields': ('source_location', 'destination_location')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Dates', {
            'fields': ('created_at', 'sent_at', 'received_at', 'cancelled_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Utilisateurs', {
            'fields': ('created_by', 'sent_by', 'received_by', 'cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
    )

    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Articles'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    actions = ['send_transfers', 'receive_transfers']

    @admin.action(description='Envoyer les transferts sélectionnés')
    def send_transfers(self, request, queryset):
        for transfer in queryset.filter(status__in=['draft', 'pending']):
            try:
                transfer.send(request.user)
                self.message_user(request, f"Transfert {transfer.reference} envoyé.")
            except Exception as e:
                self.message_user(request, f"Erreur pour {transfer.reference}: {e}", level='error')

    @admin.action(description='Recevoir les transferts sélectionnés')
    def receive_transfers(self, request, queryset):
        for transfer in queryset.filter(status='in_transit'):
            try:
                transfer.receive(request.user)
                self.message_user(request, f"Transfert {transfer.reference} reçu.")
            except Exception as e:
                self.message_user(request, f"Erreur pour {transfer.reference}: {e}", level='error')


@admin.register(TransferItem)
class TransferItemAdmin(admin.ModelAdmin):
    list_display = ['transfer', 'product', 'quantity', 'received_quantity', 'variance', 'unit_cost']
    list_filter = ['transfer__status', 'transfer__enterprise']
    search_fields = ['product__name', 'transfer__reference']
    raw_id_fields = ['transfer', 'product']

    def variance(self, obj):
        return obj.variance
    variance.short_description = 'Écart'
