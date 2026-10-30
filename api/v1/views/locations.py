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

    # Rôle : utilise LocationListSerializer pour la liste et LocationSerializer pour les autres actions.
    # Liens : appelée par DRF ; serializers dans api/v1/serializers/locations.py.
    def get_serializer_class(self):
        if self.action == 'list':
            return LocationListSerializer
        return LocationSerializer

    # Rôle : remplace la version du mixin pour renseigner à la fois l'entreprise et le créateur de l'emplacement.
    # Liens : POST /api/v1/locations/ ; remplace EnterpriseViewSetMixin.perform_create (apps/core/mixins.py).
    def perform_create(self, serializer):
        user = self.request.user
        enterprise = user.enterprise if hasattr(user, 'enterprise') else None
        serializer.save(enterprise=enterprise, created_by=user)

    # Rôle : renvoie les emplacements de type warehouse de l'entreprise, sans pagination.
    # Liens : route GET /api/v1/locations/warehouses/ ; filtrage d'entreprise via apps/core/mixins.py.
    @action(detail=False, methods=['get'])
    def warehouses(self, request):
        """List only warehouses"""
        queryset = self.get_queryset().filter(location_type='warehouse')
        serializer = LocationListSerializer(queryset, many=True)
        return Response(serializer.data)

    # Rôle : renvoie les emplacements de type boutique de l'entreprise, sans pagination.
    # Liens : route GET /api/v1/locations/boutiques/ ; filtrage d'entreprise via apps/core/mixins.py.
    @action(detail=False, methods=['get'])
    def boutiques(self, request):
        """List only boutiques"""
        queryset = self.get_queryset().filter(location_type='boutique')
        serializer = LocationListSerializer(queryset, many=True)
        return Response(serializer.data)

    # Rôle : renvoie toutes les lignes de stock de l'emplacement visé, sans pagination.
    # Liens : route GET /api/v1/locations/<id>/stock/ ; lit LocationStock (apps/locations/models.py).
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        """Get stock levels for a location"""
        location = self.get_object()
        stocks = LocationStock.objects.filter(location=location).select_related('product')
        serializer = LocationStockSerializer(stocks, many=True)
        return Response(serializer.data)

    # Rôle : renvoie le stock faible de l'emplacement selon le seuil de LocationStock, pas celui du produit.
    # Liens : route GET /api/v1/locations/<id>/low_stock/ ; LocationStock.is_low_stock (apps/locations/models.py).
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

    # Rôle : filtre via le mixin, puis par entreprise et par emplacement de l'utilisateur (sauf owner et admin).
    # Liens : appelée par DRF ; EnterpriseViewSetMixin (apps/core/mixins.py) filtre sur enterprise.
    # LocationStock n'a pas ce champ : hors superuser, un utilisateur avec entreprise obtient une FieldError.
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

    # Rôle : renvoie les lignes de stock faible visibles par l'utilisateur, filtrées en Python.
    # Liens : route GET /api/v1/location-stocks/low_stock_alerts/ ; get_queryset() et LocationStock.is_low_stock.
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """Get all low stock alerts"""
        queryset = self.get_queryset()
        low_stock = [s for s in queryset if s.is_low_stock]
        serializer = self.get_serializer(low_stock, many=True)
        return Response(serializer.data)

    # Rôle : renvoie les lignes visibles par l'utilisateur dont la quantité est nulle ou négative.
    # Liens : route GET /api/v1/location-stocks/out_of_stock/ ; dépend de get_queryset() ; lit LocationStock.
    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get all out of stock items"""
        queryset = self.get_queryset().filter(quantity__lte=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
