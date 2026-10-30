# Stock Control & POS - Database Schema

## Overview

This document defines the MySQL database schema for the Stock Control & Point of Sale application built with Django.

---

## 1. Authentication & Users

### `users` (extends Django's AbstractUser)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email (used for login) |
| username | VARCHAR(150) | UNIQUE, NOT NULL | Username for login |
| password | VARCHAR(255) | NOT NULL | Hashed password |
| first_name | VARCHAR(100) | NOT NULL | User's first name |
| last_name | VARCHAR(100) | NOT NULL | User's last name |
| phone | VARCHAR(20) | NULL | Phone number |
| role | ENUM | NOT NULL | 'admin', 'manager', 'stock_manager', 'cashier', 'accountant' |
| is_active | BOOLEAN | DEFAULT TRUE | Account enabled/disabled |
| last_login | DATETIME | NULL | Last login timestamp |
| created_at | DATETIME | AUTO | Account creation date |
| updated_at | DATETIME | AUTO | Last update date |

**Role Permissions:**
- **admin**: Full access to all features
- **manager** (Gérant): Products, stock, reports, customers, user management (except admin)
- **stock_manager** (Gestionnaire de stock): Stock entries/exits only
- **cashier** (Caissier): POS, basic customer info only
- **accountant** (Comptable/Auditeur): Read-only reports, export data

### `action_logs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| user_id | BIGINT | FK → users | User who performed action |
| action_type | VARCHAR(50) | NOT NULL | 'login', 'logout', 'create', 'update', 'delete' |
| entity_type | VARCHAR(50) | NOT NULL | 'product', 'sale', 'stock_movement', etc. |
| entity_id | BIGINT | NULL | ID of affected entity |
| description | TEXT | NULL | Human-readable description |
| old_value | TEXT | NULL | Previous value (JSON for auditing changes) |
| new_value | TEXT | NULL | New value (JSON for auditing changes) |
| ip_address | VARCHAR(45) | NULL | User's IP address |
| created_at | DATETIME | AUTO | Action timestamp |

**Indexes:**
- `idx_action_logs_user` on `user_id`
- `idx_action_logs_entity` on `entity_type`, `entity_id`
- `idx_action_logs_date` on `created_at`
- `idx_action_logs_type` on `action_type`

---

## 2. Products & Categories

### `categories`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Category name |
| description | TEXT | NULL | Category description |
| is_active | BOOLEAN | DEFAULT TRUE | Active/inactive status |
| created_at | DATETIME | AUTO | Creation date |
| updated_at | DATETIME | AUTO | Last update date |

### `products`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| category_id | BIGINT | FK → categories | Product category |
| name | VARCHAR(200) | NOT NULL | Product name |
| description | TEXT | NULL | Product description |
| barcode | VARCHAR(50) | UNIQUE, NULL | Barcode/product code |
| sku | VARCHAR(50) | UNIQUE, NULL | Internal SKU |
| unit | ENUM | NOT NULL | 'piece', 'sachet', 'carton', 'kg', 'liter' |
| purchase_price | DECIMAL(12,2) | NOT NULL | Buying price |
| sale_price | DECIMAL(12,2) | NOT NULL | Selling price |
| tax_rate | DECIMAL(5,2) | DEFAULT 0.00 | Tax percentage (e.g., 18.00 for 18%) |
| min_stock_threshold | INT | DEFAULT 0 | Alert when stock falls below |
| is_popular | BOOLEAN | DEFAULT FALSE | Show in POS quick buttons |
| is_active | BOOLEAN | DEFAULT TRUE | Active/inactive status |
| image | VARCHAR(255) | NULL | Product image path |
| created_at | DATETIME | AUTO | Creation date |
| updated_at | DATETIME | AUTO | Last update date |

**Indexes:**
- `idx_products_category` on `category_id`
- `idx_products_barcode` on `barcode`
- `idx_products_name` on `name`

### `product_packagings` (Conditionnements)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| product_id | BIGINT | FK → products | Parent product |
| name | VARCHAR(50) | NOT NULL | Packaging name (e.g., 'Carton', 'Pack') |
| quantity_per_unit | DECIMAL(12,3) | NOT NULL | Units in this packaging (e.g., 12) |
| barcode | VARCHAR(50) | UNIQUE, NULL | Barcode for this packaging |
| sale_price | DECIMAL(12,2) | NULL | Optional special price for packaging |
| is_active | BOOLEAN | DEFAULT TRUE | Active/inactive status |
| created_at | DATETIME | AUTO | Creation date |

**Indexes:**
- `idx_product_packagings_product` on `product_id`
- `idx_product_packagings_barcode` on `barcode`

**Example:** Product "Soda 33cl" has packaging "Carton" with quantity_per_unit=24

---

## 3. Stock Management

### `stock`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| product_id | BIGINT | FK → products, UNIQUE | One stock record per product |
| quantity | DECIMAL(12,3) | NOT NULL, DEFAULT 0 | Current quantity in stock |
| last_restock_date | DATE | NULL | Last date stock was replenished |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Indexes:**
- `idx_stock_product` on `product_id`

### `stock_movements`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| product_id | BIGINT | FK → products | Affected product |
| user_id | BIGINT | FK → users | User who made the movement |
| movement_type | ENUM | NOT NULL | 'entry', 'exit' |
| reason | ENUM | NOT NULL | See reason codes below |
| quantity | DECIMAL(12,3) | NOT NULL | Quantity moved (always positive) |
| unit_cost | DECIMAL(12,2) | NULL | Cost per unit (for entries) |
| reference | VARCHAR(100) | NULL | External reference (invoice #, etc.) |
| notes | TEXT | NULL | Additional notes |
| created_at | DATETIME | AUTO | Movement timestamp |

**Reason codes:**
- **Entry**: 'purchase', 'customer_return', 'correction', 'initial_stock', 'transfer_in', 'other_entry'
- **Exit**: 'sale', 'manual_sale', 'loss', 'breakage', 'expiration', 'correction', 'transfer_out', 'other_exit'

Note: 'manual_sale' is for "ventes hors POS" (sales made outside the POS system)

**Indexes:**
- `idx_stock_movements_product` on `product_id`
- `idx_stock_movements_date` on `created_at`
- `idx_stock_movements_type` on `movement_type`
- `idx_stock_movements_user` on `user_id`
- `idx_stock_movements_reason` on `reason`

---

## 4. Customers

### `customers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| name | VARCHAR(200) | NOT NULL | Customer full name |
| phone | VARCHAR(20) | NULL | Phone number |
| email | VARCHAR(255) | NULL | Email address |
| address | TEXT | NULL | Physical address |
| notes | TEXT | NULL | Internal notes about customer |
| credit_limit | DECIMAL(12,2) | DEFAULT 0.00 | Maximum allowed credit |
| current_balance | DECIMAL(12,2) | DEFAULT 0.00 | Current outstanding credit balance |
| total_purchases | DECIMAL(12,2) | DEFAULT 0.00 | Total amount spent (for top customers) |
| purchase_count | INT | DEFAULT 0 | Number of purchases (for frequency) |
| loyalty_points | INT | DEFAULT 0 | Accumulated loyalty points |
| is_active | BOOLEAN | DEFAULT TRUE | Active/inactive status |
| created_at | DATETIME | AUTO | Creation date |
| updated_at | DATETIME | AUTO | Last update date |

**Indexes:**
- `idx_customers_name` on `name`
- `idx_customers_phone` on `phone`
- `idx_customers_balance` on `current_balance`
- `idx_customers_purchases` on `total_purchases`

---

## 5. Sales & POS

### `sales`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| sale_number | VARCHAR(50) | UNIQUE, NOT NULL | Unique sale reference (e.g., 'VNT-20251204-0001') |
| customer_id | BIGINT | FK → customers, NULL | Customer (NULL for anonymous) |
| user_id | BIGINT | FK → users | Cashier who made the sale |
| subtotal | DECIMAL(12,2) | NOT NULL | Sum before discount and tax |
| discount_amount | DECIMAL(12,2) | DEFAULT 0.00 | Discount applied |
| discount_percent | DECIMAL(5,2) | DEFAULT 0.00 | Discount percentage |
| tax_amount | DECIMAL(12,2) | DEFAULT 0.00 | Total tax amount |
| total_amount | DECIMAL(12,2) | NOT NULL | Final amount to pay |
| amount_paid | DECIMAL(12,2) | NOT NULL | Amount received from customer |
| change_amount | DECIMAL(12,2) | DEFAULT 0.00 | Change returned |
| payment_method | ENUM | NOT NULL | 'cash', 'mobile_money', 'card', 'credit' |
| payment_reference | VARCHAR(100) | NULL | Transaction ID for mobile/card |
| status | ENUM | DEFAULT 'completed' | 'completed', 'refunded', 'cancelled' |
| notes | TEXT | NULL | Sale notes |
| created_at | DATETIME | AUTO | Sale timestamp |

**Indexes:**
- `idx_sales_customer` on `customer_id`
- `idx_sales_user` on `user_id`
- `idx_sales_date` on `created_at`
- `idx_sales_number` on `sale_number`
- `idx_sales_status` on `status`
- `idx_sales_payment` on `payment_method`

### `sale_items`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| sale_id | BIGINT | FK → sales | Parent sale |
| product_id | BIGINT | FK → products | Product sold |
| product_name | VARCHAR(200) | NOT NULL | Product name (snapshot) |
| quantity | DECIMAL(12,3) | NOT NULL | Quantity sold |
| unit_price | DECIMAL(12,2) | NOT NULL | Sale price per unit (snapshot) |
| purchase_price | DECIMAL(12,2) | NOT NULL | Purchase price per unit (snapshot for profit) |
| discount_amount | DECIMAL(12,2) | DEFAULT 0.00 | Item-level discount |
| tax_rate | DECIMAL(5,2) | DEFAULT 0.00 | Tax rate applied |
| tax_amount | DECIMAL(12,2) | DEFAULT 0.00 | Tax amount |
| total_price | DECIMAL(12,2) | NOT NULL | Line total |

**Indexes:**
- `idx_sale_items_sale` on `sale_id`
- `idx_sale_items_product` on `product_id`

---

## 6. Customer Credits

### `customer_credits`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| customer_id | BIGINT | FK → customers | Customer with credit |
| sale_id | BIGINT | FK → sales | Sale that created the debt |
| original_amount | DECIMAL(12,2) | NOT NULL | Original credit amount |
| remaining_amount | DECIMAL(12,2) | NOT NULL | Current outstanding balance |
| due_date | DATE | NULL | Expected payment date |
| status | ENUM | DEFAULT 'pending' | 'pending', 'partial', 'paid' |
| notes | TEXT | NULL | Notes about the credit |
| created_at | DATETIME | AUTO | Credit creation date |
| updated_at | DATETIME | AUTO | Last update date |

**Indexes:**
- `idx_customer_credits_customer` on `customer_id`
- `idx_customer_credits_status` on `status`
- `idx_customer_credits_sale` on `sale_id`
- `idx_customer_credits_due_date` on `due_date`

### `credit_payments`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| credit_id | BIGINT | FK → customer_credits | Related credit |
| user_id | BIGINT | FK → users | User who recorded payment |
| amount | DECIMAL(12,2) | NOT NULL | Amount paid |
| payment_method | ENUM | NOT NULL | 'cash', 'mobile_money', 'card' |
| payment_reference | VARCHAR(100) | NULL | Transaction reference |
| notes | TEXT | NULL | Payment notes |
| created_at | DATETIME | AUTO | Payment timestamp |

**Indexes:**
- `idx_credit_payments_credit` on `credit_id`
- `idx_credit_payments_date` on `created_at`
- `idx_credit_payments_user` on `user_id`

---

## 7. Accounting & Expenses

### `expenses`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| expense_category_id | BIGINT | FK → expense_categories, NULL | Expense category |
| user_id | BIGINT | FK → users | User who recorded expense |
| amount | DECIMAL(12,2) | NOT NULL | Expense amount |
| description | TEXT | NOT NULL | Expense description |
| expense_date | DATE | NOT NULL | Date expense occurred |
| payment_method | ENUM | NOT NULL | 'cash', 'mobile_money', 'card', 'bank_transfer' |
| reference | VARCHAR(100) | NULL | Receipt/invoice number |
| supplier | VARCHAR(200) | NULL | Supplier/vendor name |
| is_recurring | BOOLEAN | DEFAULT FALSE | Recurring expense flag |
| notes | TEXT | NULL | Additional notes |
| created_at | DATETIME | AUTO | Record creation date |
| updated_at | DATETIME | AUTO | Last update date |

**Indexes:**
- `idx_expenses_category` on `expense_category_id`
- `idx_expenses_date` on `expense_date`
- `idx_expenses_user` on `user_id`

### `expense_categories`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Category name |
| description | TEXT | NULL | Category description |
| is_active | BOOLEAN | DEFAULT TRUE | Active/inactive status |
| created_at | DATETIME | AUTO | Creation date |

**Default categories:** 'Rent', 'Utilities', 'Salaries', 'Supplies', 'Transport', 'Marketing', 'Maintenance', 'Taxes', 'Other'

### `cash_register_sessions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| user_id | BIGINT | FK → users | Cashier who opened session |
| opening_balance | DECIMAL(12,2) | NOT NULL | Cash at session start |
| closing_balance | DECIMAL(12,2) | NULL | Cash at session end |
| expected_balance | DECIMAL(12,2) | NULL | Calculated expected balance |
| difference | DECIMAL(12,2) | NULL | Difference (closing - expected) |
| opened_at | DATETIME | NOT NULL | Session open time |
| closed_at | DATETIME | NULL | Session close time |
| status | ENUM | DEFAULT 'open' | 'open', 'closed' |
| notes | TEXT | NULL | Session notes/discrepancies |

**Indexes:**
- `idx_cash_sessions_user` on `user_id`
- `idx_cash_sessions_date` on `opened_at`
- `idx_cash_sessions_status` on `status`

### `daily_summaries`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| summary_date | DATE | UNIQUE, NOT NULL | Date of summary |
| total_sales | DECIMAL(12,2) | DEFAULT 0.00 | Total sales amount |
| total_expenses | DECIMAL(12,2) | DEFAULT 0.00 | Total expenses amount |
| total_cash | DECIMAL(12,2) | DEFAULT 0.00 | Cash payment total |
| total_mobile_money | DECIMAL(12,2) | DEFAULT 0.00 | Mobile money total |
| total_card | DECIMAL(12,2) | DEFAULT 0.00 | Card payment total |
| total_credit | DECIMAL(12,2) | DEFAULT 0.00 | Credit sales total |
| credit_collected | DECIMAL(12,2) | DEFAULT 0.00 | Credit payments collected (encaissements) |
| total_cost_of_goods | DECIMAL(12,2) | DEFAULT 0.00 | Total purchase cost of items sold |
| gross_profit | DECIMAL(12,2) | DEFAULT 0.00 | Gross profit (sales - cost of goods) |
| number_of_sales | INT | DEFAULT 0 | Transaction count |
| number_of_customers | INT | DEFAULT 0 | Unique customers served |
| net_profit | DECIMAL(12,2) | DEFAULT 0.00 | Net profit (gross profit - expenses) |
| created_at | DATETIME | AUTO | Record creation time |
| updated_at | DATETIME | AUTO | Last update time |

**Indexes:**
- `idx_daily_summaries_date` on `summary_date`

**Note:** This table is automatically populated/updated by a daily aggregation job or trigger.

---

## 8. Store Configuration

### `store_settings`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | BIGINT | PK, AUTO_INCREMENT | Primary key |
| key | VARCHAR(100) | UNIQUE, NOT NULL | Setting key |
| value | TEXT | NULL | Setting value |
| updated_at | DATETIME | AUTO | Last update date |

**Default settings:**
```
store_name          → "Ma Boutique"
store_address       → ""
store_phone         → ""
store_email         → ""
store_logo          → ""
store_website       → ""
currency_code       → "XOF"
currency_symbol     → "FCFA"
default_tax_rate    → "0"
date_format         → "DD/MM/YYYY"
time_format         → "24h"
receipt_header      → ""
receipt_footer      → "Merci pour votre achat!"
receipt_show_logo   → "true"
language            → "fr"
low_stock_alert     → "true"
allow_negative_stock → "false"
auto_backup         → "true"
backup_frequency    → "daily"
loyalty_program_enabled → "false"
loyalty_points_rate → "1000"   (Amount spent to earn 1 point)
```

---

## Entity Relationship Diagram (Text)

```
users ─────────────────┬──────────────────┬─────────────────┐
                       │                  │                 │
                       ▼                  ▼                 ▼
               action_logs            sales         stock_movements
                                        │                  │
                                        │                  │
                                        ▼                  │
                                   sale_items              │
                                        │                  │
                                        ▼                  ▼
categories ──────► products ◄──────────┴──────────────────┘
                       │
                       ▼
                    stock


customers ─────────► sales
    │                  │
    │                  ▼
    └──────► customer_credits
                  │
                  ▼
            credit_payments


expense_categories ──────► expenses
                              │
                              ▼
                          (accounting)


users ──────► cash_register_sessions
```

---

## Django Model Naming Convention

| Table Name | Django Model | App |
|------------|--------------|-----|
| users | User (custom) | accounts |
| action_logs | ActionLog | accounts |
| categories | Category | products |
| products | Product | products |
| product_packagings | ProductPackaging | products |
| stock | Stock | stock |
| stock_movements | StockMovement | stock |
| customers | Customer | customers |
| customer_credits | CustomerCredit | customers |
| credit_payments | CreditPayment | customers |
| sales | Sale | pos |
| sale_items | SaleItem | pos |
| expenses | Expense | accounting |
| expense_categories | ExpenseCategory | accounting |
| cash_register_sessions | CashRegisterSession | accounting |
| daily_summaries | DailySummary | accounting |
| store_settings | StoreSetting | settings |

---

## Notes

1. **Decimal Precision**: All monetary values use DECIMAL(12,2) for accuracy
2. **Quantity Precision**: Stock quantities use DECIMAL(12,3) to support kg/liter measurements
3. **Soft Delete**: Use `is_active` flag instead of hard deletes for products/customers (never hard delete)
4. **Audit Trail**: `action_logs` tracks all important operations:
   - User logins/logouts
   - Product/category deletions
   - Large stock movements (define threshold in settings)
   - User account changes (enable/disable)
   - Price changes
5. **Snapshots**: `sale_items` stores product_name, unit_price, and purchase_price at time of sale for historical accuracy
6. **Stock Updates**: Stock should be updated via Django signals when sales/movements occur to maintain consistency
7. **Customer Balance**: `customers.current_balance` should be updated automatically when:
   - Credit sales are created
   - Credit payments are recorded
   - Credits are marked as paid
8. **Customer Statistics**: Update `total_purchases` and `purchase_count` on each sale
9. **Packaging**: Use `product_packagings` for carton/pack conversions (e.g., 1 carton = 12 units)
10. **Manual Sales**: Stock exits with reason='manual_sale' for "ventes hors POS" (sales made outside POS)
11. **Sale Number Format**: Use pattern like "VNT-YYYYMMDD-NNNN" for unique sale references
12. **Security**: All passwords must be hashed (use Django's built-in authentication)
13. **Performance**: Add database indexes on frequently queried fields (dates, foreign keys, status)
14. **Backup**: Implement regular automated backups as per `store_settings.auto_backup`

## Required Reports (from specifications)

### 1. Dashboard (Tableau de bord)
- Daily/weekly/monthly revenue (chiffre d'affaires)
- Number of sales today
- Top selling products
- Products below minimum stock threshold (alerte stock minimum)
- Recent sales list
- Total customers with outstanding credits

### 2. Sales Reports (Rapports de ventes)
- Filter by: date range, product, cashier, payment method
- Sales totals by day
- Sales totals by product
- Sales totals by cashier
- Revenue breakdown by payment method
- Profit margins (sales price - purchase price)

### 3. Stock Reports (Rapports de stock)
- Current stock levels (all products)
- Products at or below minimum threshold
- Stock movement history (filtered by product/date range)
- Stock valuation report (quantity × purchase price)
- Entry/exit summary by reason

### 4. Customer Reports (Rapports clients)
- Top customers by total spending (`total_purchases` DESC)
- Top customers by purchase frequency (`purchase_count` DESC)
- Customers with outstanding credits (WHERE `current_balance` > 0)
- Customer purchase history
- Credit aging report (overdue credits)

### 5. Accounting Reports (Rapports comptables)
- Daily/weekly/monthly expense summary by category
- Cash flow report (revenue - expenses)
- Profit & Loss statement (revenue - cost of goods - expenses)
- Payment method breakdown (cash vs mobile money vs card vs credit)
- Cash register reconciliation (expected vs actual)
- Net profit trends over time
- Expense trends by category

### 6. Export Formats
- **PDF**: Formatted, printable reports
- **Excel**: Raw data for further analysis
- All reports must support both formats
