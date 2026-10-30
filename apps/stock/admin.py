from django.contrib import admin
from .models import Stock, StockMovement


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'is_low_stock', 'last_restock_date', 'updated_at')
    list_filter = ('last_restock_date', 'updated_at')
    search_fields = ('product__name', 'product__barcode')
    readonly_fields = ('updated_at',)
    ordering = ('product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'reason', 'quantity', 'user', 'reference', 'created_at')
    list_filter = ('movement_type', 'reason', 'created_at', 'user')
    search_fields = ('product__name', 'product__barcode', 'reference', 'notes')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Product Information', {
            'fields': ('product',)
        }),
        ('Movement Details', {
            'fields': ('movement_type', 'reason', 'quantity', 'unit_cost')
        }),
        ('Reference', {
            'fields': ('reference', 'notes')
        }),
        ('User & Date', {
            'fields': ('user', 'created_at')
        }),
    )
