from rest_framework import serializers
from apps.accounts.models import User, ActionLog


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    password = serializers.CharField(write_only=True, required=False, style={'input_type': 'password'})
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'full_name', 'phone', 'role', 'role_display', 'is_active', 
            'is_staff', 'is_superuser', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_login', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def create(self, validated_data):
        """Create user with hashed password"""
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """Update user and handle password separately"""
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """Minimal serializer for user listings"""
    
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email', 'role', 'role_display', 'is_active']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ActionLogSerializer(serializers.ModelSerializer):
    """Serializer for ActionLog model"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = ActionLog
        fields = [
            'id', 'user', 'user_name', 'action_type', 'action_type_display',
            'entity_type', 'entity_id', 'description', 'old_value', 'new_value',
            'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """Hide IP address from non-admin users"""
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user and request.user.role not in ['admin', 'manager']:
            data.pop('ip_address', None)
        return data

