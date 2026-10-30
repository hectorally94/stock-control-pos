from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from apps.stock.models import Stock, StockMovement
from api.v1.serializers import StockSerializer, StockMovementSerializer
from api.v1.permissions import IsStockManager


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Stock management.
    Stock managers can view and update stock levels.
    """
    
    queryset = Stock.objects.select_related('product', 'product__category').all()
    serializer_class = StockSerializer
    permission_classes = [IsStockManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product']
    search_fields = ['product__name', 'product__barcode']
    ordering_fields = ['quantity', 'updated_at']
    ordering = ['product__name']
    
    # Rôle : renvoie les lignes de Stock dont la quantité atteint le seuil du produit, filtrées en Python.
    # Liens : route GET /api/v1/stock/low_stock_alerts/ ; utilise Stock.is_low_stock (apps/stock/models.py).
    @action(detail=False, methods=['get'])
    def low_stock_alerts(self, request):
        """
        Get all products with low stock.
        """
        low_stock_items = []
        for stock in self.get_queryset():
            if stock.is_low_stock:
                low_stock_items.append(stock)
        
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for StockMovement management.
    Records all stock entries and exits.
    """
    
    queryset = StockMovement.objects.select_related('product', 'user').all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsStockManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'movement_type', 'reason', 'user']
    search_fields = ['product__name', 'reference', 'notes']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    # Rôle : enregistre le mouvement au nom de l'utilisateur connecté.
    # Liens : POST /api/v1/stock-movements/ ; StockMovement.save() (apps/stock/models.py) met à jour les stocks.
    def perform_create(self, serializer):
        """Set current user when creating movement"""
        serializer.save(user=self.request.user)
    
    # Rôle : filtre les mouvements par product_id, start_date, end_date et movement_type, avec pagination.
    # Liens : route GET /api/v1/stock-movements/movement_history/ ; lit StockMovement (apps/stock/models.py).
    @action(detail=False, methods=['get'])
    def movement_history(self, request):
        """
        Get stock movement history with filters.
        Query params: product_id, start_date, end_date, movement_type
        """
        queryset = self.get_queryset()
        
        # Filter by product
        product_id = request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Filter by movement type
        movement_type = request.query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

