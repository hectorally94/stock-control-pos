# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 5.0 Stock Control & POS system with REST API (DRF) + Django templates frontend (TailwindCSS + AlpineJS). MySQL in production, SQLite in-memory for tests.

## Common Commands

```bash
# Setup
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data          # Creates default expense categories + store settings
python manage.py createsuperuser

# Run
python manage.py runserver          # Web: http://127.0.0.1:8000, API docs: /api/v1/docs/

# Test (uses SQLite in-memory)
pytest                              # All tests with coverage, stops on first failure
pytest tests/test_api.py -v         # Specific file
pytest tests/test_api.py::TestSaleAPI::test_create_sale -v  # Single test
pytest --cov=apps --cov-report=html # Coverage report

# Database
docker-compose up -d mysql          # Start MySQL via Docker
python manage.py makemigrations
python manage.py migrate

# Daily summaries
python manage.py generate_daily_summary
python manage.py generate_daily_summary --date 2025-12-04
python manage.py generate_daily_summary --backfill 2025-01-01 2025-12-31
```

## Architecture

### App Structure (under `apps/`)

- **core** - Enterprise model, abstract base models (TimeStampedModel, AuditableModel, EnterpriseAwareModel)
- **accounts** - Custom User model with role-based access, ActionLog audit trail
- **products** - Category, Product, ProductPackaging (unit conversions)
- **stock** - Stock levels, StockMovement with auto-update via model save()
- **pos** - Sale, SaleItem with signals for stock/audit (`apps/pos/signals.py`)
- **customers** - Customer, CustomerCredit, CreditPayment (debt tracking)
- **accounting** - Expenses, CashRegisterSession, DailySummary
- **locations** - Location, LocationStock (multi-location inventory)
- **transfers** - Stock transfers between locations
- **reports** - Reporting views and utilities
- **settings** - StoreSetting (key-value configuration)

### API Layer (`api/v1/`)

- **views/** - ViewSets for each app
- **serializers/** - DRF serializers (often split by action: list/create/detail)
- **permissions.py** - Role-based permission classes: `IsAdminOrManager`, `IsStockManager`, `IsCashier`, `IsAccountant`, `IsAdminOnly`
- **auth/** - JWT authentication (SimpleJWT) at `/api/v1/auth/login/`
- **urls.py** - Router registration for all endpoints

### Critical Data Flow

**Sales → Stock**: Sale creation → SaleItem signals (`apps/pos/signals.py`) → StockMovement creation → Stock.quantity auto-update via `StockMovement.save()` (`apps/stock/models.py`)

For manual stock operations, create StockMovement directly. For sales, signals handle it automatically.

## Model Conventions

- **Money**: `DecimalField(max_digits=12, decimal_places=2)` - always
- **Quantities**: `DecimalField(max_digits=12, decimal_places=3)` - supports kg/liter
- **Soft delete**: `is_active` flag, never hard delete products/customers
- **Explicit `db_table`** and indexes in Meta class
- **Sale snapshots**: SaleItem stores product_name/unit_price at sale time
- **Foreign keys**: Use `RESTRICT` on critical relationships

## API Patterns

```python
# Serializer switching by action
def get_serializer_class(self):
    if self.action == 'list': return SaleListSerializer
    elif self.action == 'create': return SaleCreateSerializer
    return SaleSerializer

# Custom actions
@action(detail=False, methods=['get'])
def today_summary(self, request): ...

# Always use select_related/prefetch_related in querysets
queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items')
```

## Testing

Uses pytest + pytest-django + factory_boy. Factories in `tests/factories.py`, fixtures in `tests/conftest.py`.

Key fixtures: `api_client`, `admin_client`, `cashier_client`, `manager_client`, `stock_manager_client` (pre-authenticated by role).

```python
@pytest.mark.django_db
def test_create_sale(self, cashier_client, customer_factory, product_factory):
    customer = customer_factory()
    product = product_factory()
    # cashier_client is pre-authenticated with cashier role
```

## User Roles

| Role | Access | Permission Class |
|------|--------|-----------------|
| admin/owner | Full access | `IsAdminOnly` |
| manager | Products, stock, reports, customers, users | `IsAdminOrManager` |
| warehouse_manager / boutique_manager | Stock and transfer operations | `IsStockManager` |
| stock_manager | Stock entry/exit only | `IsStockManager` |
| cashier | POS and read customers | `IsCashier` |
| accountant | Read-only all | `IsAccountant` |

## Localization

French primary language. Currency: XOF/FCFA displayed as "FB". Timezone: Africa/Abidjan. Dates: DD/MM/YYYY format.

## Key Files

- `stock_control/settings.py` - Django config (uses `.env` for DB credentials)
- `api/v1/permissions.py` - All role-based permission classes
- `apps/pos/signals.py` - Sale→stock automation
- `apps/stock/models.py` - StockMovement.save() auto-updates Stock
- `tests/conftest.py` - pytest fixtures and DB config
- `tests/factories.py` - factory_boy model factories
- `docs/database_schema.md` - Complete DB schema documentation
- `API_QUICK_REFERENCE.md` - API endpoint reference
