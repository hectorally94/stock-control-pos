from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.locations.models import Location, LocationStock
from apps.core.permissions import IsManager, CanManageStock
from apps.core.mixins import EnterpriseViewSetMixin
from api.v1.serializers.locations import (
    LocationSerializer, LocationListSerializer, LocationStockSerializer
)


class LocationViewSet(EnterpriseViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Location management.
    Managers can manage locations within their enterprise.
    """

    queryset = Location.objects.select_related('enterprise', 'manager', 'created_by')
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated, IsManager]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['location_type', 'is_main_warehouse', 'is_active']
    search_fields = ['name', 'code', 'address', 'phone', 'email']
    ordering_fields = ['name', 'location_type', 'created_at']
    ordering = ['location_type', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return LocationListSerializer
        return LocationSerializer

    def perform_create(self, serializer):
        user = self.request.user
        enterprise = user.enterprise if hasattr(user, 'enterprise') else None
        serializer.save(enterprise=enterprise, created_by=user)

    @action(detail=False, methods=['get'])
    def warehouses(self, request):
        """List only warehouses"""
        queryset = self.get_queryset().filter(location_type='warehouse')
        serializer = LocationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def boutiques(self, request):
        """List only boutiques"""
        queryset = self.get_queryset().filter(location_type='boutique')
        serializer = LocationListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        """Get stock levels for a location"""
        location = self.get_object()
        stocks = LocationStock.objects.filter(location=location).select_related('product')
        serializer = LocationStockSerializer(stocks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def low_stock(self, request, pk=None):
        """Get low stock items for a location"""
        location = self.get_object()
        stocks = LocationStock.objects.filter(
            location=location
        ).select_related('product')

        # Filter for low stock
        low_stock_items = [s for s in stocks if s.is_low_stock]
        serializer = LocationStockSerializer(low_stock_items, many=True)
        return Response(serializer.data)


class LocationStockViewSet(EnterpriseViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for LocationStock management.
    Stock managers can view and update stock levels.
    """

    queryset = LocationStock.objects.select_related('location', 'product')
    serializer_class = LocationStockSerializer
    permission_classes = [IsAuthenticated, CanManageStock]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['location', 'product']
    search_fields = ['product__name', 'location__name']
    ordering_fields = ['quantity', 'updated_at']
    ordering = ['location', 'product']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by enterprise
        if hasattr(user, 'enterprise') and user.enterprise:
            queryset = queryset.filter(location__enterprise=user.enterprise)

        # If user has a specific location, further filter
        if hasattr(user, 'location') and user.location and user.role not in ['owner', 'admin']:
            queryset = queryset.filter(location=user.location)

        return queryset

    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Get all low stock alerts"""
        queryset = self.get_queryset()
        low_stock = [s for s in queryset if s.is_low_stock]
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get all out of stock items"""
        queryset = self.get_queryset().filter(quantity__lte=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
