from rest_framework import serializers
from apps.stock.models import Stock, StockMovement
from api.v1.serializers.products import ProductListSerializer
from api.v1.serializers.accounts import UserListSerializer


class StockSerializer(serializers.ModelSerializer):
    """Serializer for Stock model"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_details = ProductListSerializer(source='product', read_only=True)
    is_low_stock = serializers.ReadOnlyField()
    min_stock_threshold = serializers.IntegerField(source='product.min_stock_threshold', read_only=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'product', 'product_name', 'product_details',
            'quantity', 'is_low_stock', 'min_stock_threshold',
            'last_restock_date', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    """Serializer for StockMovement model"""

    product_name = serializers.CharField(source='product.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'location', 'user', 'user_name',
            'movement_type', 'movement_type_display', 'reason',
            'quantity', 'unit_cost', 'reference', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    # Rôle : refuse une quantité nulle ou négative ; le sens vient de movement_type, pas du signe.
    # Liens : appelée par DRF pour StockMovementViewSet ; StockMovement.save() (apps/stock/models.py) l'applique.
    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError('La quantité doit être positive')
        return value

