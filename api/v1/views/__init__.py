# Rôle : regroupe et réexporte tous les ViewSets de l'API, un fichier par domaine.
# Liens : importé par api/v1/urls.py, qui enregistre ces ViewSets dans son routeur.
from .accounts import UserViewSet, ActionLogViewSet
from .products import CategoryViewSet, ProductViewSet, ProductPackagingViewSet
from .stock import StockViewSet, StockMovementViewSet
from .customers import CustomerViewSet, CustomerCreditViewSet, CreditPaymentViewSet
from .pos import SaleViewSet, SaleItemViewSet
from .accounting import ExpenseCategoryViewSet, ExpenseViewSet, CashRegisterSessionViewSet, DailySummaryViewSet
from .settings import StoreSettingViewSet
from .core import EnterpriseViewSet
from .locations import LocationViewSet, LocationStockViewSet
from .transfers import TransferViewSet, TransferItemViewSet

__all__ = [
    # Core
    'EnterpriseViewSet',
    # Accounts
    'UserViewSet',
    'ActionLogViewSet',
    # Locations
    'LocationViewSet',
    'LocationStockViewSet',
    # Transfers
    'TransferViewSet',
    'TransferItemViewSet',
    # Products
    'CategoryViewSet',
    'ProductViewSet',
    'ProductPackagingViewSet',
    # Stock
    'StockViewSet',
    'StockMovementViewSet',
    # Customers
    'CustomerViewSet',
    'CustomerCreditViewSet',
    'CreditPaymentViewSet',
    # POS
    'SaleViewSet',
    'SaleItemViewSet',
    # Accounting
    'ExpenseCategoryViewSet',
    'ExpenseViewSet',
    'CashRegisterSessionViewSet',
    'DailySummaryViewSet',
    # Settings
    'StoreSettingViewSet',
]

