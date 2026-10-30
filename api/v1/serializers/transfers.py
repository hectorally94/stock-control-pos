from rest_framework import serializers
from apps.transfers.models import Transfer, TransferItem


class TransferItemSerializer(serializers.ModelSerializer):
    """Serializer for TransferItem model"""

    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    variance = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = TransferItem
        fields = [
            'id', 'transfer', 'product', 'product_name', 'product_unit',
            'quantity', 'received_quantity', 'unit_cost', 'notes',
            'variance', 'total_cost'
        ]


class TransferItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating TransferItem"""

    class Meta:
        model = TransferItem
        fields = ['product', 'quantity', 'unit_cost', 'notes']


class TransferSerializer(serializers.ModelSerializer):
    """Serializer for Transfer model"""

    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    source_location_name = serializers.CharField(source='source_location.name', read_only=True)
    destination_location_name = serializers.CharField(source='destination_location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    sent_by_name = serializers.CharField(source='sent_by.get_full_name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.get_full_name', read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    items = TransferItemSerializer(many=True, read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id', 'enterprise', 'enterprise_name', 'reference',
            'source_location', 'source_location_name',
            'destination_location', 'destination_location_name',
            'status', 'status_display', 'notes',
            'created_at', 'updated_at', 'sent_at', 'received_at', 'cancelled_at',
            'created_by', 'created_by_name',
            'sent_by', 'sent_by_name',
            'received_by', 'received_by_name',
            'cancelled_by', 'cancellation_reason',
            'total_items', 'total_quantity', 'items'
        ]
        read_only_fields = [
            'reference', 'created_at', 'updated_at', 'sent_at', 'received_at', 'cancelled_at',
            'created_by', 'sent_by', 'received_by', 'cancelled_by'
        ]


class TransferListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing transfers"""

    source_location_name = serializers.CharField(source='source_location.name', read_only=True)
    destination_location_name = serializers.CharField(source='destination_location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Transfer
        fields = [
            'id', 'reference',
            'source_location', 'source_location_name',
            'destination_location', 'destination_location_name',
            'status', 'status_display',
            'total_items', 'created_at'
        ]


class TransferCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a transfer with items"""

    items = TransferItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Transfer
        fields = ['source_location', 'destination_location', 'notes', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        # Set enterprise from user
        if hasattr(user, 'enterprise') and user.enterprise:
            validated_data['enterprise'] = user.enterprise

        validated_data['created_by'] = user
        transfer = Transfer.objects.create(**validated_data)

        for item_data in items_data:
            TransferItem.objects.create(transfer=transfer, **item_data)

        return transfer


class TransferSendSerializer(serializers.Serializer):
    """Serializer for sending a transfer"""
    pass


class TransferReceiveSerializer(serializers.Serializer):
    """Serializer for receiving a transfer with quantity adjustments"""

    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='List of items with received_quantity adjustments'
    )

    def validate_items(self, value):
        for item in value:
            if 'id' not in item:
                raise serializers.ValidationError('Each item must have an id')
        return value


class TransferCancelSerializer(serializers.Serializer):
    """Serializer for cancelling a transfer"""

    reason = serializers.CharField(required=True, help_text='Reason for cancellation')
