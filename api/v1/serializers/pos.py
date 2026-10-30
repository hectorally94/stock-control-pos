from rest_framework import serializers
from apps.pos.models import Sale, SaleItem
from api.v1.serializers.customers import CustomerListSerializer
from api.v1.serializers.accounts import UserListSerializer


class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer for SaleItem model"""

    profit = serializers.ReadOnlyField()

    class Meta:
        model = SaleItem
        fields = [
            'id', 'sale', 'product', 'product_name', 'quantity',
            'unit_price', 'purchase_price', 'discount_amount',
            'tax_rate', 'tax_amount', 'total_price', 'profit'
        ]
        read_only_fields = ['id', 'sale']


class SaleItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SaleItem (nested in sale creation).

    Only `product` and `quantity` are required; `unit_price` and `total_price`
    are computed server-side from the product when omitted.
    """

    class Meta:
        model = SaleItem
        fields = [
            'product', 'quantity', 'unit_price', 'discount_amount',
            'tax_rate', 'tax_amount', 'total_price'
        ]
        extra_kwargs = {
            'unit_price': {'required': False},
            'total_price': {'required': False},
            'discount_amount': {'required': False},
            'tax_rate': {'required': False},
            'tax_amount': {'required': False},
        }

    # Rôle : refuse une quantité nulle ou négative sur une ligne de vente.
    # Liens : appelée par DRF pour chaque élément de items de SaleCreateSerializer (POST /api/v1/sales/).
    def validate_quantity(self, value):
        """Ensure quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError('La quantité doit être positive')
        return value


class SaleSerializer(serializers.ModelSerializer):
    """Serializer for Sale model"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    cashier_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer', 'customer_name',
            'user', 'cashier_name', 'subtotal', 'discount_amount',
            'discount_percent', 'tax_amount', 'total_amount',
            'amount_paid', 'change_amount', 'payment_method',
            'payment_method_display', 'payment_reference', 'status',
            'status_display', 'notes', 'items', 'created_at'
        ]
        read_only_fields = ['id', 'sale_number', 'created_at']
    
    # Rôle : hors crédit, exige amount_paid >= total_amount, en reprenant les valeurs existantes si absentes.
    # Liens : appelée par DRF sur PUT/PATCH /api/v1/sales/<id>/ ; la création passe par SaleCreateSerializer.
    def validate(self, data):
        """Validate payment amounts"""
        payment_method = data.get('payment_method', self.instance.payment_method if self.instance else None)
        total_amount = data.get('total_amount', self.instance.total_amount if self.instance else 0)
        amount_paid = data.get('amount_paid', self.instance.amount_paid if self.instance else 0)
        
        # For credit sales, amount_paid can be less than total_amount
        if payment_method != 'credit' and amount_paid < total_amount:
            raise serializers.ValidationError({
                'amount_paid': 'Le montant payé doit être supérieur ou égal au total pour les paiements non-crédit'
            })
        
        return data
    
    # Rôle : ajoute un numéro de vente via Sale.generate_sale_number() puis crée la vente sans ses lignes.
    # Liens : aucune route ne l'atteint : SaleViewSet.get_serializer_class() prend SaleCreateSerializer pour create.
    def create(self, validated_data):
        """Generate sale number before creation"""
        if not validated_data.get('sale_number'):
            validated_data['sale_number'] = Sale.generate_sale_number()
        return super().create(validated_data)


class SaleListSerializer(serializers.ModelSerializer):
    """Minimal serializer for sale listings"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    cashier_name = serializers.CharField(source='user.get_full_name', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'sale_number', 'customer_name', 'cashier_name',
            'total_amount', 'payment_method', 'status',
            'item_count', 'created_at'
        ]
    
    # Rôle : compte les lignes de la vente pour le champ item_count.
    # Liens : appelée par DRF sur GET /api/v1/sales/ (SaleViewSet, api/v1/views/pos.py) ; lit obj.items.
    def get_item_count(self, obj):
        return obj.items.count()


class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating sales with nested items.

    Clients only need to send `items` (each with `product` + `quantity`) and a
    `payment_method`. Line prices and sale totals are computed server-side from
    the products, but any explicitly-provided value is respected.
    """

    items = SaleItemCreateSerializer(many=True)

    class Meta:
        model = Sale
        fields = [
            'sale_number', 'customer', 'subtotal', 'discount_amount',
            'discount_percent', 'tax_amount', 'total_amount',
            'amount_paid', 'change_amount', 'payment_method',
            'payment_reference', 'status', 'notes', 'items'
        ]
        read_only_fields = ['sale_number']
        extra_kwargs = {
            'subtotal': {'required': False},
            'discount_amount': {'required': False},
            'discount_percent': {'required': False},
            'tax_amount': {'required': False},
            'total_amount': {'required': False},
            'amount_paid': {'required': False},
            'change_amount': {'required': False},
        }

    # Rôle : calcule prix, sous-total, remise, total et monnaie si absents, puis crée la vente et ses SaleItem.
    # Liens : via SaleViewSet.perform_create() ; déclenche apps/pos/signals.py et apps/customers/signals.py.
    def create(self, validated_data):
        """Create sale with nested items, computing prices/totals as needed."""
        from decimal import Decimal

        items_data = validated_data.pop('items')

        zero = Decimal('0')
        discount_amount = validated_data.get('discount_amount') or zero
        discount_percent = validated_data.get('discount_percent') or zero

        # Compute each line and the subtotal.
        subtotal = zero
        computed_items = []
        for item_data in items_data:
            product = item_data.get('product')
            quantity = item_data.get('quantity') or zero

            unit_price = item_data.get('unit_price')
            if unit_price is None and product is not None:
                unit_price = product.sale_price
            unit_price = unit_price or zero

            item_discount = item_data.get('discount_amount') or zero
            line_total = item_data.get('total_price')
            if line_total is None:
                line_total = quantity * unit_price - item_discount

            item_data['unit_price'] = unit_price
            item_data['total_price'] = line_total
            if product is not None:
                item_data['product_name'] = product.name
                item_data['purchase_price'] = product.purchase_price

            subtotal += line_total
            computed_items.append(item_data)

        # Apply a percentage discount only when no explicit amount was given.
        if discount_percent and not validated_data.get('discount_amount'):
            discount_amount = subtotal * discount_percent / 100

        total_amount = validated_data.get('total_amount')
        if total_amount is None:
            total_amount = subtotal - discount_amount

        amount_paid = validated_data.get('amount_paid')
        if amount_paid is None:
            amount_paid = zero if validated_data.get('payment_method') == 'credit' else total_amount

        change_amount = validated_data.get('change_amount')
        if change_amount is None:
            change_amount = max(zero, amount_paid - total_amount)

        validated_data.update({
            'sale_number': Sale.generate_sale_number(),
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'total_amount': total_amount,
            'amount_paid': amount_paid,
            'change_amount': change_amount,
        })

        sale = Sale.objects.create(**validated_data)
        for item_data in computed_items:
            SaleItem.objects.create(sale=sale, **item_data)

        return sale

