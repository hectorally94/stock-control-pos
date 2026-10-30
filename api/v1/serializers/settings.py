from rest_framework import serializers
from apps.settings.models import StoreSetting


class StoreSettingSerializer(serializers.ModelSerializer):
    """Serializer for StoreSetting model"""
    
    class Meta:
        model = StoreSetting
        fields = ['id', 'key', 'value', 'updated_at']
        read_only_fields = ['id', 'updated_at']
    
    # Rôle : refuse une clé contenant des espaces et enregistre la clé en minuscules.
    # Liens : appelée par DRF pour le CRUD de StoreSettingViewSet ; son action set_setting() ne passe pas par elle.
    def validate_key(self, value):
        """Ensure key is lowercase with underscores"""
        if ' ' in value:
            raise serializers.ValidationError('La clé ne doit pas contenir d\'espaces')
        return value.lower()

