from rest_framework import serializers
from apps.locations.models import Location, LocationStock


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model"""

    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Location
        fields = [
            'id', 'enterprise', 'enterprise_name', 'name', 'code',
            'location_type', 'location_type_display',
            'address', 'phone', 'email',
            'manager', 'manager_name',
            'is_main_warehouse', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']


class LocationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing locations"""

    location_type_display = serializers.CharField(source='get_location_type_display', read_only=True)

    class Meta:
        model = Location
        fields = ['id', 'name', 'code', 'location_type', 'location_type_display', 'is_main_warehouse', 'is_active']


class LocationStockSerializer(serializers.ModelSerializer):
    """Serializer for LocationStock model"""

    location_name = serializers.CharField(source='location.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = LocationStock
        fields = [
            'id', 'location', 'location_name',
            'product', 'product_name', 'product_unit',
            'quantity', 'min_stock_threshold', 'max_stock_threshold',
            'last_restock_date', 'updated_at',
            'is_low_stock', 'is_out_of_stock'
        ]
        read_only_fields = ['updated_at']
