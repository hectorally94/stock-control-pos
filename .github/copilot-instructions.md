# Stock Control & POS - AI Agent Instructions

## Architecture Overview

Django 6.0 + MySQL POS application with REST API (DRF) + Django templates frontend.

**App Boundaries** (under `apps/`):
- `accounts` → Custom User model with role-based access, ActionLog audit trail
- `products` → Category, Product, ProductPackaging (unit conversions)
- `stock` → Stock levels, StockMovement with **auto-update via model save()**
- `pos` → Sale, SaleItem with **signals for stock/audit** (`apps/pos/signals.py`)
- `customers` → Customer, CustomerCredit, CreditPayment (debt tracking)
- `accounting` → Expenses, CashRegisterSession, DailySummary
- `settings` → StoreSetting (key-value configuration)

**Data Flow**: Sales → SaleItem signals → StockMovement creation → Stock.quantity auto-update

## Developer Commands

```bash
# Setup
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # Creates expense categories + store settings
python manage.py createsuperuser

# Run
python manage.py runserver          # Web: http://127.0.0.1:8000
                                    # API: http://127.0.0.1:8000/api/v1/docs/

# Test (uses SQLite in-memory, see tests/conftest.py)
pytest                              # Runs with coverage, stops on first failure
pytest tests/test_api.py::TestSaleAPI -v

# Daily summary generation
python manage.py generate_daily_summary                    # Yesterday
python manage.py generate_daily_summary --date 2025-12-04
python manage.py generate_daily_summary --backfill 2025-01-01 2025-12-31
```

## Model Conventions

```python
# Money: always DECIMAL(12,2)
total_amount = models.DecimalField(max_digits=12, decimal_places=2)

# Quantities: DECIMAL(12,3) for kg/liter support
quantity = models.DecimalField(max_digits=12, decimal_places=3)

# Soft delete: use is_active flag, never hard delete products/customers
is_active = models.BooleanField(default=True)

# Explicit db_table names and indexes
class Meta:
    db_table = 'customers'
    indexes = [models.Index(fields=['name'], name='idx_customers_name')]

# Sale snapshots: store product_name/unit_price at sale time (SaleItem model)
```

## API Patterns

**Location**: `api/v1/` - ViewSets in `views/`, Serializers in `serializers/`

```python
# Role-based permissions (api/v1/permissions.py)
from api.v1.permissions import IsAdminOrManager, IsCashier, IsStockManager

# Custom actions pattern
@action(detail=False, methods=['get'])
def today_summary(self, request):
    ...

# Serializer switching by action
def get_serializer_class(self):
    if self.action == 'list': return SaleListSerializer
    elif self.action == 'create': return SaleCreateSerializer
    return SaleSerializer
```

**Auth**: JWT via SimpleJWT at `/api/v1/auth/login/` → returns `access` + `refresh` tokens

## Stock Update Pattern

Stock updates happen in TWO places - understand which to use:

1. **StockMovement.save()** (`apps/stock/models.py`) - Updates Stock.quantity on create
2. **POS signals** (`apps/pos/signals.py`) - Creates StockMovement on SaleItem creation

For manual stock operations, create StockMovement. For sales, signals handle it automatically.

## User Roles

| Role | Access | Permission Class |
|------|--------|-----------------|
| admin | Full access | `IsAdminOnly` |
| manager | Products, stock, reports, customers | `IsAdminOrManager` |
| stock_manager | Stock entry/exit only | `IsStockManager` |
| cashier | POS and read customers | `IsCashier` |
| accountant | Read-only all | `IsAccountant` |

## Testing

Uses pytest + factory_boy. Factories in `tests/factories.py`:

```python
# Example usage in tests
def test_create_sale(self, cashier_client, customer_factory, product_factory):
    customer = customer_factory()
    product = product_factory()
    # cashier_client is pre-authenticated with cashier role
```

Key fixtures: `api_client`, `admin_client`, `cashier_client`, `manager_client`, `stock_manager_client`

## Key Files Reference

- Schema: `docs/database_schema.md`
- API docs: `API_QUICK_REFERENCE.md`
- Settings: `stock_control/settings.py` (uses `.env` for DB config)
- URLs: Web at `/`, API at `/api/v1/`, Swagger at `/api/v1/docs/`
- Signals: `apps/pos/signals.py` (sale→stock), no signals.py in stock app (uses save())

## Localization

French primary (error messages, labels). Currency: XOF/FCFA with "FB" symbol.
