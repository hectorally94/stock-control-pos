from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.core.models import Enterprise
from apps.core.permissions import IsOwner, IsStaffOrOwner
from api.v1.serializers.core import EnterpriseSerializer, EnterpriseListSerializer


class EnterpriseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Enterprise management.
    Only owners and admins can manage enterprises.
    """

    queryset = Enterprise.objects.all()
    serializer_class = EnterpriseSerializer
    permission_classes = [IsAuthenticated, IsStaffOrOwner]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active', 'currency']
    search_fields = ['name', 'code', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return EnterpriseListSerializer
        return EnterpriseSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Enterprise.objects.all()
        # Regular users can only see their own enterprise
        if hasattr(user, 'enterprise') and user.enterprise:
            return Enterprise.objects.filter(id=user.enterprise.id)
        return Enterprise.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an enterprise"""
        enterprise = self.get_object()
        enterprise.is_active = True
        enterprise.save()
        return Response({'status': 'Enterprise activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an enterprise"""
        enterprise = self.get_object()
        enterprise.is_active = False
        enterprise.save()
        return Response({'status': 'Enterprise deactivated'})
