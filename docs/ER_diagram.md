# Stock Control & POS - Entity Relationship Diagram

## Physical ER Diagram

```mermaid
erDiagram
    %% User relationships
    users ||--o{ action_logs : "performs"
    users ||--o{ sales : "creates"
    users ||--o{ stock_movements : "records"
    users ||--o{ expenses : "records"
    users ||--o{ cash_register_sessions : "opens"
    users ||--o{ credit_payments : "records"
    
    %% Product relationships
    categories ||--o{ products : "contains"
    products ||--o{ product_packagings : "has"
    products ||--|| stock : "has"
    products ||--o{ stock_movements : "affects"
    products ||--o{ sale_items : "sold_in"
    
    %% Customer relationships
    customers ||--o{ sales : "makes"
    customers ||--o{ customer_credits : "owes"
    
    %% Sales relationships
    sales ||--o{ sale_items : "contains"
    sales ||--|| customer_credits : "creates_debt"
    
    %% Credit relationships
    customer_credits ||--o{ credit_payments : "receives"
    
    %% Expense relationships
    expense_categories ||--o{ expenses : "categorizes"
    
    users {
        BIGINT id PK
        VARCHAR email UK
        VARCHAR username UK
        VARCHAR password
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR phone
        ENUM role "admin,manager,stock_manager,cashier,accountant"
        BOOLEAN is_active
        DATETIME last_login
        DATETIME created_at
        DATETIME updated_at
    }
    
    action_logs {
        BIGINT id PK
        BIGINT user_id FK
        VARCHAR action_type
        VARCHAR entity_type
        BIGINT entity_id
        TEXT description
        TEXT old_value
        TEXT new_value
        VARCHAR ip_address
        DATETIME created_at
    }
    
    categories {
        BIGINT id PK
        VARCHAR name UK
        TEXT description
        BOOLEAN is_active
        DATETIME created_at
        DATETIME updated_at
    }
    
    products {
        BIGINT id PK
        BIGINT category_id FK
        VARCHAR name
        TEXT description
        VARCHAR barcode UK
        VARCHAR sku UK
        ENUM unit "piece,sachet,carton,kg,liter"
        DECIMAL purchase_price
        DECIMAL sale_price
        DECIMAL tax_rate
        INT min_stock_threshold
        BOOLEAN is_popular
        BOOLEAN is_active
        VARCHAR image
        DATETIME created_at
        DATETIME updated_at
    }
    
    product_packagings {
        BIGINT id PK
        BIGINT product_id FK
        VARCHAR name
        DECIMAL quantity_per_unit
        VARCHAR barcode UK
        DECIMAL sale_price
        BOOLEAN is_active
        DATETIME created_at
    }
    
    stock {
        BIGINT id PK
        BIGINT product_id FK_UK
        DECIMAL quantity
        DATE last_restock_date
        DATETIME updated_at
    }
    
    stock_movements {
        BIGINT id PK
        BIGINT product_id FK
        BIGINT user_id FK
        ENUM movement_type "entry,exit"
        ENUM reason
        DECIMAL quantity
        DECIMAL unit_cost
        VARCHAR reference
        TEXT notes
        DATETIME created_at
    }
    
    customers {
        BIGINT id PK
        VARCHAR name
        VARCHAR phone
        VARCHAR email
        TEXT address
        TEXT notes
        DECIMAL credit_limit
        DECIMAL current_balance
        DECIMAL total_purchases
        INT purchase_count
        INT loyalty_points
        BOOLEAN is_active
        DATETIME created_at
        DATETIME updated_at
    }
    
    sales {
        BIGINT id PK
        VARCHAR sale_number UK
        BIGINT customer_id FK
        BIGINT user_id FK
        DECIMAL subtotal
        DECIMAL discount_amount
        DECIMAL discount_percent
        DECIMAL tax_amount
        DECIMAL total_amount
        DECIMAL amount_paid
        DECIMAL change_amount
        ENUM payment_method "cash,mobile_money,card,credit"
        VARCHAR payment_reference
        ENUM status "completed,refunded,cancelled"
        TEXT notes
        DATETIME created_at
    }
    
    sale_items {
        BIGINT id PK
        BIGINT sale_id FK
        BIGINT product_id FK
        VARCHAR product_name
        DECIMAL quantity
        DECIMAL unit_price
        DECIMAL purchase_price
        DECIMAL discount_amount
        DECIMAL tax_rate
        DECIMAL tax_amount
        DECIMAL total_price
    }
    
    customer_credits {
        BIGINT id PK
        BIGINT customer_id FK
        BIGINT sale_id FK
        DECIMAL original_amount
        DECIMAL remaining_amount
        DATE due_date
        ENUM status "pending,partial,paid"
        TEXT notes
        DATETIME created_at
        DATETIME updated_at
    }
    
    credit_payments {
        BIGINT id PK
        BIGINT credit_id FK
        BIGINT user_id FK
        DECIMAL amount
        ENUM payment_method "cash,mobile_money,card"
        VARCHAR payment_reference
        TEXT notes
        DATETIME created_at
    }
    
    expense_categories {
        BIGINT id PK
        VARCHAR name UK
        TEXT description
        BOOLEAN is_active
        DATETIME created_at
    }
    
    expenses {
        BIGINT id PK
        BIGINT expense_category_id FK
        BIGINT user_id FK
        DECIMAL amount
        TEXT description
        DATE expense_date
        ENUM payment_method "cash,mobile_money,card,bank_transfer"
        VARCHAR reference
        VARCHAR supplier
        BOOLEAN is_recurring
        TEXT notes
        DATETIME created_at
        DATETIME updated_at
    }
    
    cash_register_sessions {
        BIGINT id PK
        BIGINT user_id FK
        DECIMAL opening_balance
        DECIMAL closing_balance
        DECIMAL expected_balance
        DECIMAL difference
        DATETIME opened_at
        DATETIME closed_at
        ENUM status "open,closed"
        TEXT notes
    }
    
    daily_summaries {
        BIGINT id PK
        DATE summary_date UK
        DECIMAL total_sales
        DECIMAL total_expenses
        DECIMAL total_cash
        DECIMAL total_mobile_money
        DECIMAL total_card
        DECIMAL total_credit
        DECIMAL credit_collected
        DECIMAL total_cost_of_goods
        DECIMAL gross_profit
        INT number_of_sales
        INT number_of_customers
        DECIMAL net_profit
        DATETIME created_at
        DATETIME updated_at
    }
    
    store_settings {
        BIGINT id PK
        VARCHAR key UK
        TEXT value
        DATETIME updated_at
    }
```

## Legend

- **PK**: Primary Key
- **FK**: Foreign Key
- **UK**: Unique Key
- **||--o{**: One-to-Many relationship
- **||--||**: One-to-One relationship

## Key Relationships

1. **users → sales**: One user (cashier) creates many sales
2. **users → stock_movements**: One user records many stock movements
3. **users → expenses**: One user records many expenses
4. **categories → products**: One category contains many products
5. **products → stock**: One product has one stock record (1:1)
6. **products → product_packagings**: One product has many packaging options
7. **sales → sale_items**: One sale contains many items
8. **customers → sales**: One customer makes many sales
9. **customers → customer_credits**: One customer has many credit records
10. **customer_credits → credit_payments**: One credit receives many payments
11. **expense_categories → expenses**: One category has many expenses

## Cardinality Summary

| Relationship | Type | Description |
|--------------|------|-------------|
| users → action_logs | 1:N | One user performs many actions |
| users → sales | 1:N | One cashier creates many sales |
| categories → products | 1:N | One category has many products |
| products → stock | 1:1 | One product has one stock record |
| products → sale_items | 1:N | One product sold in many sales |
| sales → sale_items | 1:N | One sale has many line items |
| customers → sales | 1:N | One customer makes many purchases |
| sales → customer_credits | 1:1 | One credit sale creates one credit record |
| customer_credits → credit_payments | 1:N | One credit receives many payments |

