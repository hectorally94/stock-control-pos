# Rôle : définit EnterpriseSerializer (détail) et EnterpriseListSerializer (liste), qui convertissent en JSON.
# Liens : utilisé par api/v1/views/core.py ; modèle Enterprise de apps/core/models.py.
from rest_framework import serializers
from apps.core.models import Enterprise


class EnterpriseSerializer(serializers.ModelSerializer):
    """Serializer for Enterprise model"""

    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = Enterprise
        fields = [
            'id', 'name', 'code', 'address', 'phone', 'email',
            'tax_id', 'logo', 'currency', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']


class EnterpriseListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing enterprises"""

    class Meta:
        model = Enterprise
        fields = ['id', 'name', 'code', 'currency', 'is_active']
