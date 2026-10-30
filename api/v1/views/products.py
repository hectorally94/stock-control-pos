from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from apps.products.models import Category, Product, ProductPackaging
from apps.stock.models import Stock
from api.v1.serializers import (
    CategorySerializer, ProductSerializer, ProductListSerializer, 
    ProductPackagingSerializer
)
from api.v1.permissions import IsAdminOrManager, IsAccountant


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Category management.
    Admin and manager can CRUD, others read-only.
    """
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAccountant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Product management.
    Includes custom actions for low stock and popular products.
    """
    
    queryset = Product.objects.select_related('category').prefetch_related('packagings', 'stock_info').all()
    serializer_class = ProductSerializer
    permission_classes = [IsAccountant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'unit', 'is_popular', 'is_active']
    search_fields = ['name', 'barcode', 'sku', 'description']
    ordering_fields = ['name', 'sale_price', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Use minimal serializer for list view"""
        if self.action == 'list':
            return ProductListSerializer
        return ProductSerializer
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Get products with low stock (quantity <= min_stock_threshold).
        """
        products = []
        for product in self.get_queryset():
            try:
                if product.stock_info.is_low_stock:
                    products.append(product)
            except:
                pass
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """
        Get popular products (for POS quick buttons).
        """
        products = self.get_queryset().filter(is_popular=True, is_active=True)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stock_history(self, request, pk=None):
        """
        Get stock movement history for a product.
        """
        product = self.get_object()
        from apps.stock.models import StockMovement
        from api.v1.serializers import StockMovementSerializer
        
        movements = StockMovement.objects.filter(product=product).select_related('user')[:50]
        serializer = StockMovementSerializer(movements, many=True)
        return Response(serializer.data)


class ProductPackagingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProductPackaging management.
    """
    
    queryset = ProductPackaging.objects.select_related('product').all()
    serializer_class = ProductPackagingSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product', 'is_active']
    search_fields = ['name', 'barcode']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

