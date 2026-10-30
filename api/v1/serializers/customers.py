from rest_framework import serializers
from apps.customers.models import Customer, CustomerCredit, CreditPayment


class CreditPaymentSerializer(serializers.ModelSerializer):
    """Serializer for CreditPayment model"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = CreditPayment
        fields = [
            'id', 'credit', 'user', 'user_name', 'amount',
            'payment_method', 'payment_method_display',
            'payment_reference', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CustomerCreditSerializer(serializers.ModelSerializer):
    """Serializer for CustomerCredit model"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sale_number = serializers.CharField(source='sale.sale_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.ReadOnlyField()
    payments = CreditPaymentSerializer(many=True, read_only=True)
    
    class Meta:
        model = CustomerCredit
        fields = [
            'id', 'customer', 'customer_name', 'sale', 'sale_number',
            'original_amount', 'remaining_amount', 'due_date', 'status',
            'status_display', 'is_overdue', 'notes', 'payments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # Rôle : refuse un montant restant négatif sur un crédit client.
    # Liens : appelée par DRF pour les écritures de CustomerCreditViewSet (api/v1/views/customers.py).
    def validate_remaining_amount(self, value):
        """Ensure remaining amount is not negative"""
        if value < 0:
            raise serializers.ValidationError('Le montant restant ne peut pas être négatif')
        return value


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    
    has_outstanding_credit = serializers.ReadOnlyField()
    credits = CustomerCreditSerializer(many=True, read_only=True)
    credit_utilization = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'address', 'notes',
            'credit_limit', 'current_balance', 'has_outstanding_credit',
            'credit_utilization', 'total_purchases', 'purchase_count',
            'loyalty_points', 'is_active', 'credits',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_balance', 'total_purchases', 'purchase_count', 'loyalty_points', 'created_at', 'updated_at']
    
    # Rôle : calcule current_balance / credit_limit en pourcentage, via des float, ou 0 si la limite est nulle.
    # Liens : appelée par DRF pour les réponses détaillées de CustomerViewSet (api/v1/views/customers.py).
    def get_credit_utilization(self, obj):
        """Calculate credit utilization percentage.

        Cast to float first: a freshly created instance may still hold the
        model's float field default for current_balance, which would otherwise
        raise TypeError when divided by a Decimal credit_limit.
        """
        credit_limit = float(obj.credit_limit or 0)
        if credit_limit > 0:
            return round(float(obj.current_balance or 0) / credit_limit * 100, 2)
        return 0
    
    # Rôle : refuse une limite de crédit inférieure au solde actuel (solde 0 pour un nouveau client).
    # Liens : appelée par DRF pour CustomerViewSet ; apps/customers/signals.py refait ce contrôle avant save.
    def validate(self, data):
        """Validate credit limit"""
        credit_limit = data.get('credit_limit', self.instance.credit_limit if self.instance else 0)
        current_balance = self.instance.current_balance if self.instance else 0
        
        if current_balance > credit_limit:
            raise serializers.ValidationError({
                'credit_limit': 'La limite de crédit ne peut pas être inférieure au solde actuel'
            })
        
        return data


class CustomerListSerializer(serializers.ModelSerializer):
    """Minimal serializer for customer listings"""
    
    has_outstanding_credit = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'current_balance', 'has_outstanding_credit', 'is_active']

