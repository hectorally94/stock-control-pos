from django.contrib import admin
from .models import Customer, CustomerCredit, CreditPayment


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'current_balance', 'total_purchases', 'purchase_count', 'loyalty_points', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'phone', 'email', 'address')
    ordering = ('-total_purchases',)
    readonly_fields = ('current_balance', 'total_purchases', 'purchase_count', 'loyalty_points', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'phone', 'email', 'address')
        }),
        ('Credit Information', {
            'fields': ('credit_limit', 'current_balance')
        }),
        ('Statistics', {
            'fields': ('total_purchases', 'purchase_count', 'loyalty_points')
        }),
        ('Status & Notes', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at')
        }),
    )


class CreditPaymentInline(admin.TabularInline):
    model = CreditPayment
    extra = 0
    readonly_fields = ('user', 'amount', 'payment_method', 'payment_reference', 'created_at')
    can_delete = False


@admin.register(CustomerCredit)
class CustomerCreditAdmin(admin.ModelAdmin):
    list_display = ('customer', 'sale', 'original_amount', 'remaining_amount', 'due_date', 'status', 'is_overdue', 'created_at')
    list_filter = ('status', 'due_date', 'created_at')
    search_fields = ('customer__name', 'sale__sale_number', 'notes')
    readonly_fields = ('sale', 'original_amount', 'created_at', 'updated_at')
    date_hierarchy = 'due_date'
    ordering = ('-created_at',)
    inlines = [CreditPaymentInline]


@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ('credit', 'amount', 'payment_method', 'user', 'payment_reference', 'created_at')
    list_filter = ('payment_method', 'created_at', 'user')
    search_fields = ('credit__customer__name', 'payment_reference', 'notes')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
