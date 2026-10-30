from rest_framework import serializers
from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession, DailySummary


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Serializer for ExpenseCategory model"""
    
    expense_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description', 'is_active', 'expense_count', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_expense_count(self, obj):
        return obj.expenses.count()


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for Expense model"""
    
    category_name = serializers.CharField(source='expense_category.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_category', 'category_name', 'user', 'user_name',
            'amount', 'description', 'expense_date', 'payment_method',
            'payment_method_display', 'reference', 'supplier',
            'is_recurring', 'notes', 'created_at', 'updated_at'
        ]
        # `user` is set server-side from the authenticated request in
        # ExpenseViewSet.perform_create(), so clients must not be required to
        # send it.
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError('Le montant doit être positif')
        return value


class CashRegisterSessionSerializer(serializers.ModelSerializer):
    """Serializer for CashRegisterSession model"""
    
    cashier_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = CashRegisterSession
        fields = [
            'id', 'user', 'cashier_name', 'opening_balance',
            'closing_balance', 'expected_balance', 'difference',
            'opened_at', 'closed_at', 'status', 'status_display', 'notes'
        ]
        read_only_fields = ['id']


class DailySummarySerializer(serializers.ModelSerializer):
    """Serializer for DailySummary model"""
    
    profit_margin = serializers.SerializerMethodField()
    
    class Meta:
        model = DailySummary
        fields = [
            'id', 'summary_date', 'total_sales', 'total_expenses',
            'total_cash', 'total_mobile_money', 'total_card', 'total_credit',
            'credit_collected', 'total_cost_of_goods', 'gross_profit',
            'number_of_sales', 'number_of_customers', 'net_profit',
            'profit_margin', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_profit_margin(self, obj):
        """Calculate profit margin percentage"""
        if obj.total_sales > 0:
            return round((obj.net_profit / obj.total_sales) * 100, 2)
        return 0

