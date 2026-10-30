from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.settings.models import StoreSetting
from api.v1.serializers import StoreSettingSerializer
from api.v1.permissions import IsAdminOrManager


class StoreSettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StoreSetting management.
    Only admin and manager can modify settings.
    """
    
    queryset = StoreSetting.objects.all()
    serializer_class = StoreSettingSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['key', 'value']
    ordering_fields = ['key', 'updated_at']
    ordering = ['key']
    
    @action(detail=False, methods=['get'])
    def get_setting(self, request):
        """
        Get a specific setting by key.
        Query param: key
        """
        key = request.query_params.get('key')
        if not key:
            return Response(
                {'error': 'Le paramètre "key" est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        value = StoreSetting.get_setting(key)
        if value is not None:
            return Response({'key': key, 'value': value})
        
        return Response(
            {'message': 'Paramètre non trouvé'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=False, methods=['post'])
    def set_setting(self, request):
        """
        Set a setting value.
        Body: {key: string, value: string}
        """
        key = request.data.get('key')
        value = request.data.get('value')
        
        if not key:
            return Response(
                {'error': 'Le paramètre "key" est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        setting = StoreSetting.set_setting(key, value)
        serializer = self.get_serializer(setting)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def all_settings(self, request):
        """
        Get all settings as a dictionary.
        """
        settings = {}
        for setting in self.get_queryset():
            settings[setting.key] = setting.value
        
        return Response(settings)

