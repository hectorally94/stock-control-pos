# Rôle : réexporte les serializers des comptes, produits, stock, clients, ventes, compta et réglages.
# Liens : importé par accounts, products, stock, customers, pos, accounting et settings de api/v1/views/.
# Les serializers core, locations et transfers sont importés directement depuis leur propre fichier.
from .accounts import UserSerializer, UserListSerializer, ActionLogSerializer
from .products import CategorySerializer, ProductSerializer, ProductListSerializer, ProductPackagingSerializer
from .stock import StockSerializer, StockMovementSerializer
from .customers import CustomerSerializer, CustomerListSerializer, CustomerCreditSerializer, CreditPaymentSerializer
from .pos import SaleSerializer, SaleListSerializer, SaleItemSerializer, SaleCreateSerializer
from .accounting import ExpenseCategorySerializer, ExpenseSerializer, CashRegisterSessionSerializer, DailySummarySerializer
from .settings import StoreSettingSerializer

__all__ = [
    # Accounts
    'UserSerializer',
    'UserListSerializer',
    'ActionLogSerializer',
    # Products
    'CategorySerializer',
    'ProductSerializer',
    'ProductListSerializer',
    'ProductPackagingSerializer',
    # Stock
    'StockSerializer',
    'StockMovementSerializer',
    # Customers
    'CustomerSerializer',
    'CustomerListSerializer',
    'CustomerCreditSerializer',
    'CreditPaymentSerializer',
    # POS
    'SaleSerializer',
    'SaleListSerializer',
    'SaleItemSerializer',
    'SaleCreateSerializer',
    # Accounting
    'ExpenseCategorySerializer',
    'ExpenseSerializer',
    'CashRegisterSessionSerializer',
    'DailySummarySerializer',
    # Settings
    'StoreSettingSerializer',
]

