---
config:
  theme: default
---
erDiagram
    %% ==========================================
    %% CORE MODULE
    %% ==========================================

    Enterprise {
        bigint id PK
        string name
        string code UK
        text address
        string phone
        string email
        string tax_id
        string logo
        string currency
        boolean is_active
        datetime created_at
        datetime updated_at
        bigint created_by FK
    }

    %% ==========================================
    %% ACCOUNTS MODULE
    %% ==========================================

    User {
        bigint id PK
        string username UK
        string email UK
        string password
        string first_name
        string last_name
        string phone
        string role
        boolean is_active
        boolean is_staff
        boolean is_superuser
        datetime date_joined
        datetime last_login
        datetime created_at
        datetime updated_at
        bigint enterprise_id FK
        bigint location_id FK
    }

    ActionLog {
        bigint id PK
        string action_type
        string entity_type
        bigint entity_id
        text description
        text old_value
        text new_value
        string ip_address
        datetime created_at
        bigint user_id FK
    }

    %% ==========================================
    %% LOCATIONS MODULE
    %% ==========================================

    Location {
        bigint id PK
        string name
        string code
        string location_type
        text address
        string phone
        string email
        boolean is_main_warehouse
        boolean is_active
        datetime created_at
        datetime updated_at
        bigint enterprise_id FK
        bigint manager_id FK
        bigint created_by_id FK
    }

    LocationStock {
        bigint id PK
        decimal quantity
        decimal min_stock_threshold
        decimal max_stock_threshold
        datetime last_restock_date
        datetime updated_at
        bigint location_id FK
        bigint product_id FK
    }

    %% ==========================================
    %% PRODUCTS MODULE
    %% ==========================================

    Category {
        bigint id PK
        string name
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
        bigint enterprise_id FK
    }

    Product {
        bigint id PK
        string name
        text description
        string barcode
        string sku
        string unit
        decimal purchase_price
        decimal sale_price
        decimal tax_rate
        int min_stock_threshold
        boolean is_popular
        boolean is_active
        string image
        datetime created_at
        datetime updated_at
        bigint category_id FK
        bigint enterprise_id FK
    }

    ProductPackaging {
        bigint id PK
        string name
        decimal quantity_per_unit
        string barcode UK
        decimal sale_price
        boolean is_active
        datetime created_at
        bigint product_id FK
    }

    %% ==========================================
    %% STOCK MODULE
    %% ==========================================

    Stock {
        bigint id PK
        decimal quantity
        date last_restock_date
        datetime updated_at
        bigint product_id FK
        bigint enterprise_id FK
        bigint location_id FK
    }

    StockMovement {
        bigint id PK
        string movement_type
        string reason
        decimal quantity
        decimal unit_cost
        string reference
        text notes
        datetime created_at
        bigint product_id FK
        bigint user_id FK
        bigint enterprise_id FK
        bigint location_id FK
    }

    %% ==========================================
    %% CUSTOMERS MODULE
    %% ==========================================

    Customer {
        bigint id PK
        string name
        string phone
        string email
        text address
        text notes
        decimal credit_limit
        decimal current_balance
        decimal total_purchases
        int purchase_count
        int loyalty_points
        boolean is_active
        datetime created_at
        datetime updated_at
        bigint enterprise_id FK
    }

    CustomerCredit {
        bigint id PK
        decimal original_amount
        decimal remaining_amount
        date due_date
        string status
        text notes
        datetime created_at
        datetime updated_at
        bigint customer_id FK
        bigint sale_id FK
    }

    CreditPayment {
        bigint id PK
        decimal amount
        string payment_method
        string payment_reference
        text notes
        datetime created_at
        bigint credit_id FK
        bigint user_id FK
    }

    %% ==========================================
    %% POS MODULE
    %% ==========================================

    Sale {
        bigint id PK
        string sale_number UK
        decimal subtotal
        decimal discount_amount
        decimal discount_percent
        decimal tax_amount
        decimal total_amount
        decimal amount_paid
        decimal change_amount
        string payment_method
        string payment_reference
        string status
        text notes
        datetime created_at
        bigint customer_id FK
        bigint user_id FK
        bigint enterprise_id FK
        bigint location_id FK
    }

    SaleItem {
        bigint id PK
        string product_name
        decimal quantity
        decimal unit_price
        decimal purchase_price
        decimal discount_amount
        decimal tax_rate
        decimal tax_amount
        decimal total_price
        bigint sale_id FK
        bigint product_id FK
    }

    %% ==========================================
    %% TRANSFERS MODULE
    %% ==========================================

    Transfer {
        bigint id PK
        string reference UK
        string status
        text notes
        datetime created_at
        datetime updated_at
        datetime sent_at
        datetime received_at
        datetime cancelled_at
        text cancellation_reason
        bigint enterprise_id FK
        bigint source_location_id FK
        bigint destination_location_id FK
        bigint created_by_id FK
        bigint sent_by_id FK
        bigint received_by_id FK
        bigint cancelled_by_id FK
    }

    TransferItem {
        bigint id PK
        decimal quantity
        decimal received_quantity
        decimal unit_cost
        text notes
        bigint transfer_id FK
        bigint product_id FK
    }

    %% ==========================================
    %% ACCOUNTING MODULE
    %% ==========================================

    ExpenseCategory {
        bigint id PK
        string name
        text description
        boolean is_active
        datetime created_at
        bigint enterprise_id FK
    }

    Expense {
        bigint id PK
        decimal amount
        text description
        date expense_date
        string payment_method
        string reference
        string supplier
        boolean is_recurring
        text notes
        datetime created_at
        datetime updated_at
        bigint expense_category_id FK
        bigint user_id FK
        bigint enterprise_id FK
        bigint location_id FK
    }

    CashRegisterSession {
        bigint id PK
        decimal opening_balance
        decimal closing_balance
        decimal expected_balance
        decimal difference
        datetime opened_at
        datetime closed_at
        string status
        text notes
        bigint user_id FK
        bigint enterprise_id FK
        bigint location_id FK
    }

    DailySummary {
        bigint id PK
        date summary_date
        decimal total_sales
        decimal total_expenses
        decimal total_cash
        decimal total_mobile_money
        decimal total_card
        decimal total_credit
        decimal credit_collected
        decimal total_cost_of_goods
        decimal gross_profit
        decimal net_profit
        int number_of_sales
        int number_of_customers
        datetime created_at
        datetime updated_at
        bigint enterprise_id FK
        bigint location_id FK
    }

    %% ==========================================
    %% SETTINGS MODULE
    %% ==========================================

    StoreSetting {
        bigint id PK
        string key UK
        text value
        datetime updated_at
    }

    %% ==========================================
    %% RELATIONSHIPS
    %% ==========================================

    %% Enterprise relationships
    Enterprise ||--o{ User : "has"
    Enterprise ||--o{ Location : "has"
    Enterprise ||--o{ Category : "has"
    Enterprise ||--o{ Product : "has"
    Enterprise ||--o{ Stock : "has"
    Enterprise ||--o{ StockMovement : "has"
    Enterprise ||--o{ Customer : "has"
    Enterprise ||--o{ Sale : "has"
    Enterprise ||--o{ Transfer : "has"
    Enterprise ||--o{ ExpenseCategory : "has"
    Enterprise ||--o{ Expense : "has"
    Enterprise ||--o{ CashRegisterSession : "has"
    Enterprise ||--o{ DailySummary : "has"

    %% User relationships
    User ||--o{ ActionLog : "performs"
    User ||--o{ StockMovement : "creates"
    User ||--o{ Sale : "processes"
    User ||--o{ CreditPayment : "records"
    User ||--o{ Expense : "records"
    User ||--o{ CashRegisterSession : "opens"
    User ||--o{ Transfer : "creates"
    User }o--|| Location : "assigned_to"

    %% Location relationships
    Location ||--o{ LocationStock : "has"
    Location ||--o{ Stock : "has"
    Location ||--o{ StockMovement : "has"
    Location ||--o{ Sale : "has"
    Location ||--o{ Expense : "has"
    Location ||--o{ CashRegisterSession : "has"
    Location ||--o{ DailySummary : "has"
    Location ||--o{ Transfer : "source"
    Location ||--o{ Transfer : "destination"
    Location }o--|| User : "managed_by"

    %% Product relationships
    Category ||--o{ Product : "contains"
    Product ||--o{ ProductPackaging : "has"
    Product ||--o{ LocationStock : "has"
    Product ||--o{ Stock : "has"
    Product ||--o{ StockMovement : "tracked_in"
    Product ||--o{ SaleItem : "sold_as"
    Product ||--o{ TransferItem : "transferred_as"

    %% Customer relationships
    Customer ||--o{ Sale : "makes"
    Customer ||--o{ CustomerCredit : "has"
    CustomerCredit ||--o{ CreditPayment : "receives"
    CustomerCredit ||--|| Sale : "for"

    %% Sale relationships
    Sale ||--o{ SaleItem : "contains"

    %% Transfer relationships
    Transfer ||--o{ TransferItem : "contains"

    %% Expense relationships
    ExpenseCategory ||--o{ Expense : "categorizes"