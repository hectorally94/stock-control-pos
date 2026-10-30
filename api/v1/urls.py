# Rôle : routeur de l'API : enregistre chaque ViewSet et ajoute la documentation (schema, docs, redoc).
# Liens : ViewSets réexportés par api/v1/views/__init__.py ; inclut api/v1/auth/urls.py.
# Ce fichier est inclus sous api/v1/ par stock_control/urls.py.
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from api.v1.views import (
    # Core
    EnterpriseViewSet,
    # Accounts
    UserViewSet, ActionLogViewSet,
    # Locations
    LocationViewSet, LocationStockViewSet,
    # Transfers
    TransferViewSet, TransferItemViewSet,
    # Products
    CategoryViewSet, ProductViewSet, ProductPackagingViewSet,
    # Stock
    StockViewSet, StockMovementViewSet,
    # Customers
    CustomerViewSet, CustomerCreditViewSet, CreditPaymentViewSet,
    # POS
    SaleViewSet, SaleItemViewSet,
    # Accounting
    ExpenseCategoryViewSet, ExpenseViewSet, CashRegisterSessionViewSet, DailySummaryViewSet,
    # Settings
    StoreSettingViewSet,
)

# Create router and register viewsets
router = DefaultRouter()

# Core
router.register(r'enterprises', EnterpriseViewSet, basename='enterprise')

# Accounts
router.register(r'users', UserViewSet, basename='user')
router.register(r'action-logs', ActionLogViewSet, basename='actionlog')

# Locations
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'location-stocks', LocationStockViewSet, basename='locationstock')

# Transfers
router.register(r'transfers', TransferViewSet, basename='transfer')
router.register(r'transfer-items', TransferItemViewSet, basename='transferitem')

# Products
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'product-packagings', ProductPackagingViewSet, basename='productpackaging')

# Stock
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'stock-movements', StockMovementViewSet, basename='stockmovement')

# Customers
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'customer-credits', CustomerCreditViewSet, basename='customercredit')
router.register(r'credit-payments', CreditPaymentViewSet, basename='creditpayment')

# POS
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'sale-items', SaleItemViewSet, basename='saleitem')

# Accounting
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expensecategory')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'cash-register-sessions', CashRegisterSessionViewSet, basename='cashregistersession')
router.register(r'daily-summaries', DailySummaryViewSet, basename='dailysummary')

# Settings
router.register(r'settings', StoreSettingViewSet, basename='storesetting')

urlpatterns = [
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Authentication
    path('auth/', include('api.v1.auth.urls')),
    
    # API endpoints
    path('', include(router.urls)),
]

