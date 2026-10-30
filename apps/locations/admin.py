from django.contrib import admin
from .models import Location, LocationStock


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'enterprise', 'location_type', 'manager', 'is_main_warehouse', 'is_active']
    list_filter = ['enterprise', 'location_type', 'is_main_warehouse', 'is_active']
    search_fields = ['name', 'code', 'address', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['enterprise', 'location_type', 'name']
    raw_id_fields = ['manager']

    fieldsets = (
        (None, {
            'fields': ('enterprise', 'name', 'code', 'location_type')
        }),
        ('Configuration', {
            'fields': ('manager', 'is_main_warehouse', 'is_active')
        }),
        ('Contact', {
            'fields': ('address', 'phone', 'email')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LocationStock)
class LocationStockAdmin(admin.ModelAdmin):
    list_display = ['product', 'location', 'quantity', 'min_stock_threshold', 'is_low_stock', 'updated_at']
    list_filter = ['location__enterprise', 'location', 'location__location_type']
    search_fields = ['product__name', 'location__name']
    readonly_fields = ['updated_at']
    raw_id_fields = ['product', 'location']
    ordering = ['location', 'product']

    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Stock faible'
