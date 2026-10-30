from django.contrib import admin
from .models import ExpenseCategory, Expense, CashRegisterSession, DailySummary


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'expense_category', 'expense_date', 'payment_method', 'user', 'supplier')
    list_filter = ('expense_category', 'payment_method', 'is_recurring', 'expense_date', 'user')
    search_fields = ('description', 'supplier', 'reference', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'expense_date'
    ordering = ('-expense_date',)
    
    fieldsets = (
        ('Expense Details', {
            'fields': ('expense_category', 'description', 'amount', 'expense_date')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'reference', 'supplier')
        }),
        ('Additional Info', {
            'fields': ('is_recurring', 'notes', 'user', 'created_at', 'updated_at')
        }),
    )


@admin.register(CashRegisterSession)
class CashRegisterSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'opening_balance', 'closing_balance', 'expected_balance', 'difference', 'status', 'opened_at', 'closed_at')
    list_filter = ('status', 'user', 'opened_at')
    search_fields = ('user__username', 'notes')
    readonly_fields = ('opened_at', 'closed_at')
    date_hierarchy = 'opened_at'
    ordering = ('-opened_at',)


@admin.register(DailySummary)
class DailySummaryAdmin(admin.ModelAdmin):
    list_display = ('summary_date', 'total_sales', 'total_expenses', 'gross_profit', 'net_profit', 'number_of_sales')
    list_filter = ('summary_date',)
    search_fields = ('summary_date',)
    readonly_fields = ('summary_date', 'total_sales', 'total_expenses', 'total_cash', 'total_mobile_money', 'total_card', 'total_credit', 'credit_collected', 'total_cost_of_goods', 'gross_profit', 'number_of_sales', 'number_of_customers', 'net_profit', 'created_at', 'updated_at')
    date_hierarchy = 'summary_date'
    ordering = ('-summary_date',)
    
    # Rôle : interdit l'ajout manuel d'un résumé journalier depuis l'admin.
    # Liens : appelée par l'admin Django ; les résumés viennent notamment de la commande generate_daily_summary.
    def has_add_permission(self, request):
        return False
    
    # Rôle : rend les résumés journaliers non modifiables dans l'admin.
    # Liens : appelée par l'admin Django, pour le modèle DailySummary de apps/accounting/models.py.
    def has_change_permission(self, request, obj=None):
        return False
