-- Stock Control & POS - Database Schema
-- MySQL DDL Script for Physical Model Generation
-- Import this file into MySQL Workbench to generate ER Diagram

-- Create Database
CREATE DATABASE IF NOT EXISTS stock_control_pos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stock_control_pos;

-- ============================================================================
-- 1. Authentication & Users
-- ============================================================================

CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role ENUM('admin', 'manager', 'stock_manager', 'cashier', 'accountant') NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_role (role),
    INDEX idx_users_email (email)
) ENGINE=InnoDB COMMENT='User accounts with role-based access';

CREATE TABLE action_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id BIGINT,
    description TEXT,
    old_value TEXT COMMENT 'JSON format',
    new_value TEXT COMMENT 'JSON format',
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_action_logs_user (user_id),
    INDEX idx_action_logs_entity (entity_type, entity_id),
    INDEX idx_action_logs_date (created_at),
    INDEX idx_action_logs_type (action_type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Audit trail for all important actions';

-- ============================================================================
-- 2. Products & Categories
-- ============================================================================

CREATE TABLE categories (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_categories_name (name)
) ENGINE=InnoDB COMMENT='Product categories';

CREATE TABLE products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    barcode VARCHAR(50) UNIQUE,
    sku VARCHAR(50) UNIQUE,
    unit ENUM('piece', 'sachet', 'carton', 'kg', 'liter') NOT NULL,
    purchase_price DECIMAL(12,2) NOT NULL,
    sale_price DECIMAL(12,2) NOT NULL,
    tax_rate DECIMAL(5,2) DEFAULT 0.00,
    min_stock_threshold INT DEFAULT 0,
    is_popular BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    image VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_products_category (category_id),
    INDEX idx_products_barcode (barcode),
    INDEX idx_products_name (name),
    INDEX idx_products_sku (sku),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Product catalog';

CREATE TABLE product_packagings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT NOT NULL,
    name VARCHAR(50) NOT NULL,
    quantity_per_unit DECIMAL(12,3) NOT NULL,
    barcode VARCHAR(50) UNIQUE,
    sale_price DECIMAL(12,2),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_product_packagings_product (product_id),
    INDEX idx_product_packagings_barcode (barcode),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Product packaging conversions (e.g., 1 carton = 12 units)';

-- ============================================================================
-- 3. Stock Management
-- ============================================================================

CREATE TABLE stock (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT UNIQUE NOT NULL,
    quantity DECIMAL(12,3) NOT NULL DEFAULT 0,
    last_restock_date DATE,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock_product (product_id),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Current stock levels per product';

CREATE TABLE stock_movements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    movement_type ENUM('entry', 'exit') NOT NULL,
    reason ENUM('purchase', 'customer_return', 'correction', 'initial_stock', 'transfer_in', 'other_entry', 
                'sale', 'manual_sale', 'loss', 'breakage', 'expiration', 'transfer_out', 'other_exit') NOT NULL,
    quantity DECIMAL(12,3) NOT NULL,
    unit_cost DECIMAL(12,2),
    reference VARCHAR(100),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_stock_movements_product (product_id),
    INDEX idx_stock_movements_date (created_at),
    INDEX idx_stock_movements_type (movement_type),
    INDEX idx_stock_movements_user (user_id),
    INDEX idx_stock_movements_reason (reason),
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Stock movement history (entries and exits)';

-- ============================================================================
-- 4. Customers
-- ============================================================================

CREATE TABLE customers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    notes TEXT,
    credit_limit DECIMAL(12,2) DEFAULT 0.00,
    current_balance DECIMAL(12,2) DEFAULT 0.00,
    total_purchases DECIMAL(12,2) DEFAULT 0.00,
    purchase_count INT DEFAULT 0,
    loyalty_points INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customers_name (name),
    INDEX idx_customers_phone (phone),
    INDEX idx_customers_balance (current_balance),
    INDEX idx_customers_purchases (total_purchases)
) ENGINE=InnoDB COMMENT='Customer database';

-- ============================================================================
-- 5. Sales & POS
-- ============================================================================

CREATE TABLE sales (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sale_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id BIGINT,
    user_id BIGINT NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) DEFAULT 0.00,
    discount_percent DECIMAL(5,2) DEFAULT 0.00,
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL,
    amount_paid DECIMAL(12,2) NOT NULL,
    change_amount DECIMAL(12,2) DEFAULT 0.00,
    payment_method ENUM('cash', 'mobile_money', 'card', 'credit') NOT NULL,
    payment_reference VARCHAR(100),
    status ENUM('completed', 'refunded', 'cancelled') DEFAULT 'completed',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sales_customer (customer_id),
    INDEX idx_sales_user (user_id),
    INDEX idx_sales_date (created_at),
    INDEX idx_sales_number (sale_number),
    INDEX idx_sales_status (status),
    INDEX idx_sales_payment (payment_method),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Sales transactions';

CREATE TABLE sale_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sale_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    quantity DECIMAL(12,3) NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    purchase_price DECIMAL(12,2) NOT NULL,
    discount_amount DECIMAL(12,2) DEFAULT 0.00,
    tax_rate DECIMAL(5,2) DEFAULT 0.00,
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    total_price DECIMAL(12,2) NOT NULL,
    INDEX idx_sale_items_sale (sale_id),
    INDEX idx_sale_items_product (product_id),
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Items in each sale';

-- ============================================================================
-- 6. Customer Credits
-- ============================================================================

CREATE TABLE customer_credits (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    sale_id BIGINT NOT NULL,
    original_amount DECIMAL(12,2) NOT NULL,
    remaining_amount DECIMAL(12,2) NOT NULL,
    due_date DATE,
    status ENUM('pending', 'partial', 'paid') DEFAULT 'pending',
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_credits_customer (customer_id),
    INDEX idx_customer_credits_status (status),
    INDEX idx_customer_credits_sale (sale_id),
    INDEX idx_customer_credits_due_date (due_date),
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Customer credit/debt tracking';

CREATE TABLE credit_payments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    credit_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method ENUM('cash', 'mobile_money', 'card') NOT NULL,
    payment_reference VARCHAR(100),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_credit_payments_credit (credit_id),
    INDEX idx_credit_payments_date (created_at),
    INDEX idx_credit_payments_user (user_id),
    FOREIGN KEY (credit_id) REFERENCES customer_credits(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Payments toward customer credits';

-- ============================================================================
-- 7. Accounting & Expenses
-- ============================================================================

CREATE TABLE expense_categories (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_expense_categories_name (name)
) ENGINE=InnoDB COMMENT='Expense categories';

CREATE TABLE expenses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    expense_category_id BIGINT,
    user_id BIGINT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description TEXT NOT NULL,
    expense_date DATE NOT NULL,
    payment_method ENUM('cash', 'mobile_money', 'card', 'bank_transfer') NOT NULL,
    reference VARCHAR(100),
    supplier VARCHAR(200),
    is_recurring BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_expenses_category (expense_category_id),
    INDEX idx_expenses_date (expense_date),
    INDEX idx_expenses_user (user_id),
    FOREIGN KEY (expense_category_id) REFERENCES expense_categories(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Business expenses';

CREATE TABLE cash_register_sessions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    opening_balance DECIMAL(12,2) NOT NULL,
    closing_balance DECIMAL(12,2),
    expected_balance DECIMAL(12,2),
    difference DECIMAL(12,2),
    opened_at DATETIME NOT NULL,
    closed_at DATETIME,
    status ENUM('open', 'closed') DEFAULT 'open',
    notes TEXT,
    INDEX idx_cash_sessions_user (user_id),
    INDEX idx_cash_sessions_date (opened_at),
    INDEX idx_cash_sessions_status (status),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Cash register opening/closing sessions';

CREATE TABLE daily_summaries (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    summary_date DATE UNIQUE NOT NULL,
    total_sales DECIMAL(12,2) DEFAULT 0.00,
    total_expenses DECIMAL(12,2) DEFAULT 0.00,
    total_cash DECIMAL(12,2) DEFAULT 0.00,
    total_mobile_money DECIMAL(12,2) DEFAULT 0.00,
    total_card DECIMAL(12,2) DEFAULT 0.00,
    total_credit DECIMAL(12,2) DEFAULT 0.00,
    credit_collected DECIMAL(12,2) DEFAULT 0.00,
    total_cost_of_goods DECIMAL(12,2) DEFAULT 0.00,
    gross_profit DECIMAL(12,2) DEFAULT 0.00,
    number_of_sales INT DEFAULT 0,
    number_of_customers INT DEFAULT 0,
    net_profit DECIMAL(12,2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_daily_summaries_date (summary_date)
) ENGINE=InnoDB COMMENT='Daily financial summaries (auto-generated)';

-- ============================================================================
-- 8. Store Configuration
-- ============================================================================

CREATE TABLE store_settings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_store_settings_key (`key`)
) ENGINE=InnoDB COMMENT='Store configuration settings';

-- ============================================================================
-- Insert Default Data
-- ============================================================================

-- Default expense categories
INSERT INTO expense_categories (name, description) VALUES
('Rent', 'Monthly rent or lease payments'),
('Utilities', 'Electricity, water, internet'),
('Salaries', 'Employee wages and salaries'),
('Supplies', 'Office and store supplies'),
('Transport', 'Transportation and delivery costs'),
('Marketing', 'Advertising and promotional expenses'),
('Maintenance', 'Equipment and facility maintenance'),
('Taxes', 'Business taxes and fees'),
('Other', 'Miscellaneous expenses');

-- Default store settings
INSERT INTO store_settings (`key`, value) VALUES
('store_name', 'Ma Boutique'),
('store_address', ''),
('store_phone', ''),
('store_email', ''),
('store_logo', ''),
('store_website', ''),
('currency_code', 'XOF'),
('currency_symbol', 'FCFA'),
('default_tax_rate', '0'),
('date_format', 'DD/MM/YYYY'),
('time_format', '24h'),
('receipt_header', ''),
('receipt_footer', 'Merci pour votre achat!'),
('receipt_show_logo', 'true'),
('language', 'fr'),
('low_stock_alert', 'true'),
('allow_negative_stock', 'false'),
('auto_backup', 'true'),
('backup_frequency', 'daily'),
('loyalty_program_enabled', 'false'),
('loyalty_points_rate', '1000');
