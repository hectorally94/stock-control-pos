from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'quantity', 'unit_price', 'purchase_price', 'discount_amount', 'tax_rate', 'tax_amount', 'total_price')
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_number', 'customer', 'user', 'total_amount', 'payment_method', 'status', 'created_at')
    list_filter = ('payment_method', 'status', 'created_at', 'user')
    search_fields = ('sale_number', 'customer__name', 'user__username', 'payment_reference')
    readonly_fields = ('sale_number', 'subtotal', 'discount_amount', 'discount_percent', 'tax_amount', 'total_amount', 'amount_paid', 'change_amount', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    inlines = [SaleItemInline]
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_number', 'customer', 'user', 'status')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'discount_amount', 'discount_percent', 'tax_amount', 'total_amount')
        }),
        ('Payment', {
            'fields': ('payment_method', 'amount_paid', 'change_amount', 'payment_reference')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at')
        }),
    )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('sale', 'product_name', 'quantity', 'unit_price', 'total_price', 'profit')
    list_filter = ('sale__created_at', 'product')
    search_fields = ('sale__sale_number', 'product_name', 'product__name')
    readonly_fields = ('sale', 'product', 'product_name', 'quantity', 'unit_price', 'purchase_price', 'total_price')
    ordering = ('-sale__created_at',)
