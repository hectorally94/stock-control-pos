# API Quick Reference Guide

**Base URL**: `http://127.0.0.1:8000/api/v1/`

---

## Authentication

### Login
```bash
POST /api/v1/auth/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "role_display": "Administrator"
  }
}
```

### Get Current User
```bash
GET /api/v1/auth/me/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Refresh Token
```bash
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "YOUR_REFRESH_TOKEN"
}
```

### Logout
```bash
POST /api/v1/auth/logout/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "refresh_token": "YOUR_REFRESH_TOKEN"
}
```

---

## Products

### List Products
```bash
GET /api/v1/products/
Authorization: Bearer YOUR_ACCESS_TOKEN

# With filters
GET /api/v1/products/?category=1&is_active=true&search=coca
```

### Get Product
```bash
GET /api/v1/products/1/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Create Product
```bash
POST /api/v1/products/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "category": 1,
  "name": "Coca Cola 1.5L",
  "barcode": "123456789",
  "unit": "piece",
  "purchase_price": "500.00",
  "sale_price": "750.00",
  "min_stock_threshold": 10,
  "is_popular": true,
  "is_active": true
}
```

### Low Stock Products
```bash
GET /api/v1/products/low_stock/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Popular Products
```bash
GET /api/v1/products/popular/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Categories

### List Categories
```bash
GET /api/v1/categories/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Create Category
```bash
POST /api/v1/categories/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "name": "Boissons",
  "description": "Boissons gazeuses et jus",
  "is_active": true
}
```

---

## Stock

### List Stock
```bash
GET /api/v1/stock/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Low Stock Alerts
```bash
GET /api/v1/stock/low_stock_alerts/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Create Stock Movement (Entry)
```bash
POST /api/v1/stock-movements/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "product": 1,
  "movement_type": "entry",
  "reason": "purchase",
  "quantity": "100.000",
  "unit_cost": "500.00",
  "reference": "INV-2025-001",
  "notes": "Achat initial"
}
```

### Create Stock Movement (Exit)
```bash
POST /api/v1/stock-movements/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "product": 1,
  "movement_type": "exit",
  "reason": "loss",
  "quantity": "5.000",
  "notes": "Produits endommagés"
}
```

### Movement History
```bash
GET /api/v1/stock-movements/movement_history/?product_id=1&start_date=2025-01-01&end_date=2025-12-31
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Customers

### List Customers
```bash
GET /api/v1/customers/
Authorization: Bearer YOUR_ACCESS_TOKEN

# Search by name or phone
GET /api/v1/customers/?search=john
```

### Create Customer
```bash
POST /api/v1/customers/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "name": "Jean Dupont",
  "phone": "+225 07 12 34 56 78",
  "email": "jean@example.com",
  "address": "Abidjan, Cocody",
  "credit_limit": "50000.00",
  "is_active": true
}
```

### Top Customers
```bash
GET /api/v1/customers/top_customers/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Customers with Outstanding Credit
```bash
GET /api/v1/customers/with_credits/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Sales (POS)

### List Sales
```bash
GET /api/v1/sales/
Authorization: Bearer YOUR_ACCESS_TOKEN

# Filter by date
GET /api/v1/sales/?created_at__date=2025-12-04
```

### Create Sale
```bash
POST /api/v1/sales/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "customer": 1,
  "subtotal": "2000.00",
  "discount_amount": "0.00",
  "discount_percent": "0.00",
  "tax_amount": "0.00",
  "total_amount": "2000.00",
  "amount_paid": "2000.00",
  "change_amount": "0.00",
  "payment_method": "cash",
  "status": "completed",
  "items": [
    {
      "product": 1,
      "product_name": "Coca Cola 1.5L",
      "quantity": "2.000",
      "unit_price": "750.00",
      "purchase_price": "500.00",
      "discount_amount": "0.00",
      "tax_rate": "0.00",
      "tax_amount": "0.00",
      "total_price": "1500.00"
    },
    {
      "product": 2,
      "product_name": "Pain",
      "quantity": "1.000",
      "unit_price": "500.00",
      "purchase_price": "300.00",
      "discount_amount": "0.00",
      "tax_rate": "0.00",
      "tax_amount": "0.00",
      "total_price": "500.00"
    }
  ]
}
```

### Today's Summary
```bash
GET /api/v1/sales/today_summary/
Authorization: Bearer YOUR_ACCESS_TOKEN

Response:
{
  "count": 15,
  "total": "125000.00",
  "cash": "75000.00",
  "mobile_money": "30000.00",
  "card": "10000.00",
  "credit": "10000.00"
}
```

### Get Receipt
```bash
GET /api/v1/sales/1/receipt/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Cancel Sale (Admin/Manager only)
```bash
POST /api/v1/sales/1/cancel/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

---

## Expenses

### List Expenses
```bash
GET /api/v1/expenses/
Authorization: Bearer YOUR_ACCESS_TOKEN

# Filter by date range
GET /api/v1/expenses/?expense_date__gte=2025-01-01&expense_date__lte=2025-12-31
```

### Create Expense
```bash
POST /api/v1/expenses/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "expense_category": 1,
  "amount": "50000.00",
  "description": "Loyer du mois de décembre",
  "expense_date": "2025-12-01",
  "payment_method": "bank_transfer",
  "reference": "TRANSFER-2025-12-001",
  "supplier": "Propriétaire",
  "is_recurring": true
}
```

### Expense Summary
```bash
GET /api/v1/expenses/summary/?start_date=2025-01-01&end_date=2025-12-31
Authorization: Bearer YOUR_ACCESS_TOKEN

Response:
{
  "total": "500000.00",
  "count": 25
}
```

---

## Cash Register Sessions

### Get Current Session
```bash
GET /api/v1/cash-register-sessions/current_session/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Open Session
```bash
POST /api/v1/cash-register-sessions/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "opening_balance": "10000.00",
  "opened_at": "2025-12-04T08:00:00Z",
  "status": "open"
}
```

### Close Session
```bash
POST /api/v1/cash-register-sessions/1/close_session/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "closing_balance": "125000.00",
  "expected_balance": "125500.00"
}
```

---

## Settings

### Get All Settings
```bash
GET /api/v1/settings/all_settings/
Authorization: Bearer YOUR_ACCESS_TOKEN

Response:
{
  "store_name": "Ma Boutique",
  "currency_code": "XOF",
  "currency_symbol": "FCFA",
  "default_tax_rate": "0",
  ...
}
```

### Get Setting by Key
```bash
GET /api/v1/settings/get_setting/?key=store_name
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Set Setting
```bash
POST /api/v1/settings/set_setting/
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "key": "store_name",
  "value": "Boutique Moderne"
}
```

---

## Pagination

All list endpoints support pagination:

```bash
GET /api/v1/products/?page=2
Authorization: Bearer YOUR_ACCESS_TOKEN

Response:
{
  "count": 150,
  "next": "http://127.0.0.1:8000/api/v1/products/?page=3",
  "previous": "http://127.0.0.1:8000/api/v1/products/?page=1",
  "results": [...]
}
```

---

## Filtering

### By Field
```bash
GET /api/v1/products/?category=1&is_active=true
```

### Search
```bash
GET /api/v1/products/?search=coca
```

### Ordering
```bash
GET /api/v1/products/?ordering=-created_at
GET /api/v1/products/?ordering=name
```

### Date Range
```bash
GET /api/v1/sales/?created_at__date__gte=2025-01-01&created_at__date__lte=2025-12-31
```

---

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Role-Based Access

| Role | Can Access |
|------|------------|
| **admin** | Everything |
| **manager** | Everything except user creation/deletion |
| **stock_manager** | Stock, Stock Movements |
| **cashier** | Sales, Customers (read), Products (read) |
| **accountant** | Everything (read-only) |

---

## Documentation URLs

- **Swagger UI**: http://127.0.0.1:8000/api/v1/docs/
- **ReDoc**: http://127.0.0.1:8000/api/v1/redoc/
- **OpenAPI Schema**: http://127.0.0.1:8000/api/v1/schema/

---

## Tips

1. **Always include Authorization header** for protected endpoints
2. **Use pagination** for large datasets
3. **Filter and search** to reduce response size
4. **Check role permissions** before making requests
5. **Refresh tokens** before they expire (1 hour)
6. **Use Swagger UI** to test endpoints interactively

---

**Last Updated**: December 4, 2025  
**API Version**: v1  
**Base URL**: http://127.0.0.1:8000/api/v1/

