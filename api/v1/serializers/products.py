from rest_framework import serializers
from apps.products.models import Category, Product, ProductPackaging


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'is_active', 'product_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # Rôle : compte uniquement les produits actifs de la catégorie.
    # Liens : appelée par DRF pour CategoryViewSet (api/v1/views/products.py) ; lit Product via obj.products.
    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductPackagingSerializer(serializers.ModelSerializer):
    """Serializer for ProductPackaging model"""
    
    class Meta:
        model = ProductPackaging
        fields = [
            'id', 'product', 'name', 'quantity_per_unit', 'barcode',
            'sale_price', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)
    profit_margin = serializers.ReadOnlyField()
    packagings = ProductPackagingSerializer(many=True, read_only=True)
    stock_quantity = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'name', 'description',
            'barcode', 'sku', 'unit', 'unit_display', 'purchase_price',
            'sale_price', 'profit_margin', 'tax_rate', 'min_stock_threshold',
            'is_popular', 'is_active', 'image', 'packagings',
            'stock_quantity', 'is_low_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    # Rôle : lit obj.stock_info.quantity ; stock_info étant un gestionnaire inverse, l'except renvoie toujours 0.
    # Liens : appelée par DRF pour ProductViewSet ; stock_info vient de Stock.product (apps/stock/models.py).
    def get_stock_quantity(self, obj):
        """Get current stock quantity"""
        try:
            return float(obj.stock_info.quantity)
        except:
            return 0
    
    # Rôle : lit obj.stock_info.is_low_stock ; stock_info étant un gestionnaire inverse, l'except renvoie False.
    # Liens : appelée par DRF pour ProductViewSet ; stock_info vient de Stock.product (apps/stock/models.py).
    def get_is_low_stock(self, obj):
        """Check if stock is low"""
        try:
            return obj.stock_info.is_low_stock
        except:
            return False
    
    # Rôle : refuse un prix de vente strictement inférieur au prix d'achat ; l'égalité est acceptée.
    # Liens : appelée par DRF sur les écritures de ProductViewSet (api/v1/views/products.py).
    def validate(self, data):
        """Validate that sale_price > purchase_price"""
        purchase_price = data.get('purchase_price', self.instance.purchase_price if self.instance else None)
        sale_price = data.get('sale_price', self.instance.sale_price if self.instance else None)
        
        if purchase_price and sale_price and sale_price < purchase_price:
            raise serializers.ValidationError({
                'sale_price': 'Le prix de vente doit être supérieur au prix d\'achat'
            })
        
        return data


class ProductListSerializer(serializers.ModelSerializer):
    """Minimal serializer for product listings"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'sku', 'category_name',
            'sale_price', 'purchase_price', 'stock_quantity', 'is_active'
        ]
    
    # Rôle : lit obj.stock_info.quantity ; stock_info étant un gestionnaire inverse, l'except renvoie toujours 0.
    # Liens : appelée par DRF sur GET /api/v1/products/ et via StockSerializer (api/v1/serializers/stock.py).
    def get_stock_quantity(self, obj):
        try:
            return float(obj.stock_info.quantity)
        except:
            return 0

