# Stock Control & POS - Django Backend

Complete Django backend for Stock Control & Point of Sale application with MySQL database.

*Version française et guide d'installation : [README.fr.md](README.fr.md) · Architecture du projet : [ARCHITECTURE.md](ARCHITECTURE.md) · Base de données à importer : [database/stock_control_20261030.sql](database/stock_control_20261030.sql)*

## 🚀 Project Structure

```
AbdoulProject/
├── stock_control/          # Django project settings
├── apps/
│   ├── accounts/          # User authentication & action logs
│   ├── products/          # Products, categories, packaging
│   ├── stock/             # Stock management & movements
│   ├── customers/         # Customers & credit tracking
│   ├── pos/               # Point of Sale & sales
│   ├── accounting/        # Expenses, cash register, summaries
│   └── settings/          # Store configuration
├── docs/                  # Database schema documentation
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── manage.py              # Django management script
```

## 📊 Database Schema

**17 Tables across 7 Django apps:**
- `users`, `action_logs` (accounts)
- `categories`, `products`, `product_packagings` (products)
- `stock`, `stock_movements` (stock)
- `customers`, `customer_credits`, `credit_payments` (customers)
- `sales`, `sale_items` (pos)
- `expense_categories`, `expenses`, `cash_register_sessions`, `daily_summaries` (accounting)
- `store_settings` (settings)

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- MySQL 8.0+
- Virtual environment activated

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Copy `.env.example` to `.env` and update:
```env
DB_NAME=stock_control_pos
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=localhost
DB_PORT=3306
```

### 4. Create MySQL Database
```bash
mysql -u root -p
CREATE DATABASE stock_control_pos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Seed Default Data
```bash
python manage.py seed_data
```
This creates:
- 9 default expense categories (Rent, Utilities, Salaries, etc.)
- 21 store settings (currency, tax rate, receipt config, etc.)

### 7. Create Superuser
```bash
python manage.py createsuperuser
```

### 8. Run Development Server
```bash
python manage.py runserver
```

Access admin panel at: http://127.0.0.1:8000/admin/

## 🔑 Key Features

### Custom User Model
- Role-based access control (admin, manager, stock_manager, cashier, accountant)
- Email-based authentication
- Action logging for audit trail

### Product Management
- Categories with hierarchical organization
- Barcode/SKU support
- Multiple units (piece, sachet, carton, kg, liter)
- Product packaging conversions (e.g., 1 carton = 12 pieces)
- Tax rate per product
- Low stock alerts

### Stock Control
- Real-time stock tracking
- Entry/exit movements with reasons
- Automatic stock updates via signals
- Movement history with user tracking
- Stock valuation reports

### Point of Sale
- Unique sale numbers (VNT-YYYYMMDD-NNNN)
- Multiple payment methods (cash, mobile money, card, credit)
- Automatic stock decrement
- Profit calculation per sale
- Receipt generation

### Customer Credit Management
- Credit limits per customer
- Payment tracking
- Overdue alerts
- Partial payment support
- Automatic balance updates

### Accounting
- Expense tracking by category
- Cash register sessions (open/close)
- Daily summaries (auto-generated)
- Profit/loss calculations
- Payment method breakdowns

## 📱 Admin Interface Features

All models registered with:
- Search functionality
- Filters (date, status, category, etc.)
- Inline editing for related models
- Custom list displays
- Export capabilities

## 🔐 User Roles & Permissions

| Role | Access |
|------|--------|
| **Admin** | Full access to all features |
| **Manager** | Products, stock, reports, customers, user management |
| **Stock Manager** | Stock entries/exits only |
| **Cashier** | POS and basic customer info |
| **Accountant** | Read-only reports, data export |

## 📝 Management Commands

```bash
# Seed default data
python manage.py seed_data

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Run development server
python manage.py runserver
```

## 🗂️ Database Schema Documentation

- **database_schema.md** - Complete schema reference
- **database_schema.sql** - MySQL DDL script
- **database_schema.dbml** - DBDiagram.io format
- **ER_diagram.md** - Mermaid ER diagram
- **design_decisions.md** - Architecture documentation

## 🚦 Quick Start Guide

1. **First Time Setup:**
   ```bash
   python manage.py migrate
   python manage.py seed_data
   python manage.py createsuperuser
   ```

2. **Start Server:**
   ```bash
   python manage.py runserver
   ```

3. **Access Admin:**
   - URL: http://127.0.0.1:8000/admin/
   - Login with superuser credentials

4. **Create Test Data:**
   - Add categories (Beverages, Snacks, etc.)
   - Add products with barcodes
   - Create customers
   - Make test sales

## 🔧 Development Notes

### Automatic Behaviors
- Stock quantities update automatically on sales/movements (via signals)
- Customer balances update on credit payments
- Sale numbers auto-generate with date prefix
- Timestamps (created_at, updated_at) auto-manage

### Data Integrity
- Soft delete with `is_active` flag (never hard delete products/customers)
- Snapshots in `sale_items` preserve historical data
- Foreign key restrictions prevent orphaned records
- Audit logs track all important operations

### Performance Optimizations
- Database indexes on frequently queried fields
- `daily_summaries` table for fast reporting (no JOINs)
- Proper use of `select_related` and `prefetch_related` recommended

## 📊 Currency & Localization

- **Currency**: FCFA (XOF)
- **Language**: French (primary)
- **Date Format**: DD/MM/YYYY
- **Time Format**: 24h

## 🔄 Next Steps

### Backend (Cursor - Better for iteration)
- [ ] Implement REST API endpoints (Django REST Framework)
- [ ] Add user authentication (JWT tokens)
- [ ] Create report generation logic (PDF/Excel)
- [ ] Add signal handlers for business logic
- [ ] Implement daily summary aggregation job
- [ ] Add data validation and custom managers
- [ ] Write unit tests

### Frontend
- [ ] Build POS interface
- [ ] Create dashboard with charts
- [ ] Develop inventory management UI
- [ ] Design customer credit tracking views
- [ ] Implement reporting interface

## 📚 Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- MySQL Documentation: https://dev.mysql.com/doc/
- Project Specifications: `docs/Stock_Control_Cahier_des_Charges_v2.docx`

## ✅ Project Status

**Backend Setup: COMPLETE** ✅
- [x] Django project structure
- [x] 17 models across 7 apps
- [x] MySQL database connection
- [x] All migrations applied
- [x] Admin interface configured
- [x] Default data seeded
- [x] Documentation complete

**Ready for feature development!** 🎉
