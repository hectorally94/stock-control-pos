from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User, ActionLog
from api.v1.serializers import UserSerializer, UserListSerializer, ActionLogSerializer
from api.v1.permissions import IsAdminOnly, IsAdminOrManager


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User management.
    Only admin can create/delete users.
    Manager can view and update users (except admin users).
    """
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['created_at', 'username', 'role']
    ordering = ['-created_at']
    
    # Rôle : utilise UserListSerializer pour la liste et UserSerializer pour toutes les autres actions.
    # Liens : appelée par DRF ; serializers dans api/v1/serializers/accounts.py.
    def get_serializer_class(self):
        """Use minimal serializer for list view"""
        if self.action == 'list':
            return UserListSerializer
        return UserSerializer
    
    # Rôle : lecture et modification pour admin, owner, manager ; les autres actions pour admin et owner seulement.
    # Liens : appelée par DRF ; applique IsAdminOrManager ou IsAdminOnly (api/v1/permissions.py).
    def get_permissions(self):
        """Manager can view users but only admin can create/delete"""
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [IsAdminOrManager()]
        return [IsAdminOnly()]
    
    # Rôle : renvoie les rôles disponibles sous forme de paires value et label.
    # Liens : route GET /api/v1/users/roles/ ; lit User.ROLE_CHOICES (apps/accounts/models.py).
    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Get available user roles"""
        return Response({
            'roles': [
                {'value': role[0], 'label': role[1]}
                for role in User.ROLE_CHOICES
            ]
        })


class ActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ActionLog (read-only).
    Only admin and manager can view audit logs.
    """
    
    queryset = ActionLog.objects.select_related('user').all()
    serializer_class = ActionLogSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action_type', 'entity_type', 'user']
    search_fields = ['description', 'entity_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    # Rôle : renvoie les 50 entrées les plus récentes du journal, sans pagination.
    # Liens : route GET /api/v1/action-logs/recent/ ; lit ActionLog (apps/accounts/models.py).
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent action logs (last 50)"""
        logs = self.get_queryset()[:50]
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

