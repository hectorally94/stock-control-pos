# Cursor AI - Phase 2 Development Prompts

**Project**: Stock Control & POS Django Backend  
**Current State**: Backend complete with 17 models, migrations applied, admin configured  
**Documentation**: See `IMPLEMENTATION_REPORT.md` for full context  
**Language**: French primary (fr locale), currency FCFA/XOF  
**Target Users**: Small/medium businesses (boutiques, pharmacies, wholesalers)  

## 📚 Context Files to Reference
- `IMPLEMENTATION_REPORT.md` - Complete backend implementation details
- `docs/database_schema.md` - Full schema with all 17 tables
- `.github/copilot-instructions.md` - Project structure and requirements

---

## 📋 Table of Contents (22 Prompts)

### Phase 2A: REST API Development
| # | Prompt | Description |
|---|--------|-------------|
| 1 | Setup Django REST Framework | Install DRF, JWT, CORS, API docs |
| 2 | Create Serializers | Serializers for all 17 models with validation |
| 3 | Build ViewSets | CRUD + custom actions + permissions |
| 4 | JWT Authentication | Login, logout, refresh, user info |

### Phase 2B: Business Logic & Signals
| # | Prompt | Description |
|---|--------|-------------|
| 5 | Auto Stock Updates | Signals for stock decrement on sale |
| 6 | Auto Customer Balance | Credit tracking & loyalty points |
| 7 | Daily Summary Job | Aggregation command for DailySummary |

### Phase 2C: Frontend (Django Templates)
| # | Prompt | Description |
|---|--------|-------------|
| 8 | POS Interface | Modern cashier interface with HTMX |
| 9 | Inventory Management | Stock entry/exit/history pages |
| 10 | Reports Dashboard | Charts, metrics, filters, exports |

### Phase 2D: PDF & Excel Exports
| # | Prompt | Description |
|---|--------|-------------|
| 11 | Receipt PDF | ReportLab receipt generation |
| 12 | Excel Reports | openpyxl report exports |

### Phase 2E: Testing & Production
| # | Prompt | Description |
|---|--------|-------------|
| 13 | Unit Tests | Factory_boy, APITestCase, 80% coverage |
| 14 | Database Optimization | Query optimization, indexes, caching |
| 15 | Production Readiness | Docker, nginx, security, deployment |

### Bonus Features
| # | Prompt | Description |
|---|--------|-------------|
| 16 | Email Notifications | Receipts, alerts, reminders |
| 17 | Barcode Scanner | USB/Bluetooth scanner integration |
| 18 | Backup & Restore | Automated MySQL backups |
| 19 | Multi-Store Support | Future multi-location architecture |
| 20 | Mobile App API | Offline sync, push notifications |
| 21 | ActionLog Integration | Comprehensive audit logging |
| 22 | Localization | French UI, i18n preparation |

---

## 🔥 PHASE 2A: REST API Development

### Prompt 1: Setup Django REST Framework
```
I have a Django backend for Stock Control & POS with 17 models across 7 apps.
Read IMPLEMENTATION_REPORT.md for context.

Task: Set up Django REST Framework with JWT authentication.

1. Install packages: djangorestframework, djangorestframework-simplejwt, django-cors-headers, drf-spectacular
2. Configure settings.py:
   - Add to INSTALLED_APPS
   - Configure REST_FRAMEWORK settings with JWT auth
   - Add CORS configuration for frontend
   - Add drf-spectacular for API docs
3. Create api/ folder structure:
   - api/v1/serializers/
   - api/v1/views/
   - api/v1/urls.py
4. Update main urls.py with API routes
5. Test with /api/v1/schema/ endpoint

Show me the complete configuration.
```

---

### Prompt 2: Create Serializers for All Models
```
Create Django REST Framework serializers for all 17 models.

Requirements:
1. Read-only serializers for related objects (e.g., CategorySerializer for Product)
2. Nested serializers:
   - Sale → SaleItem relationship (items inline)
   - Product → ProductPackaging relationship (packagings inline)
   - CustomerCredit → CreditPayment relationship (payments inline)
3. Write-only password field for User (use set_password())
4. Exclude sensitive fields from ActionLog (ip_address visible to admin only)
5. Add computed fields:
   - Product: profit_margin (property already exists)
   - Stock: is_low_stock (property already exists)
   - SaleItem: profit (property already exists)
   - Customer: has_outstanding_credit (property already exists)
6. Validation:
   - sale_price must be > purchase_price (Product)
   - remaining_amount cannot be negative (CustomerCredit)
   - quantity must be positive (StockMovement, SaleItem)
   - credit_limit not exceeded (Customer)
   - amount_paid >= total_amount unless payment_method='credit' (Sale)
7. Snapshot fields: Ensure SaleItem captures product_name, unit_price, purchase_price at time of sale

Models:
- accounts: User, ActionLog
- products: Category, Product, ProductPackaging
- stock: Stock, StockMovement
- customers: Customer, CustomerCredit, CreditPayment
- pos: Sale, SaleItem
- accounting: ExpenseCategory, Expense, CashRegisterSession, DailySummary
- settings: StoreSetting

Create serializers in api/v1/serializers/ organized by app.
```

---

### Prompt 3: Build ViewSets with Permissions
```
Create ViewSets for all models with role-based permissions.

Role Permissions (from User.ROLE_CHOICES):
- admin: Full access to everything
- manager: All operations except user management (can't create/delete users)
- stock_manager: Stock operations only (Stock, StockMovement)
- cashier: POS operations (Sale, SaleItem), basic customer info (read Customer)
- accountant: Read-only access to reports (all models read-only)

Requirements:
1. ModelViewSet for CRUD operations
2. Custom permissions class: IsAdminOrManager, IsCashier, IsStockManager, IsAccountant
3. Filter backends:
   - SearchFilter: products by name/barcode, customers by name/phone, sales by sale_number
   - OrderingFilter: created_at, total_amount, quantity
   - DjangoFilterBackend: status, payment_method, date ranges, is_active
4. Custom actions:
   - products/low_stock/ → List products where Stock.quantity <= min_stock_threshold
   - products/popular/ → List products where is_popular=True (for POS quick buttons)
   - sales/today_summary/ → Aggregate today's sales (count, total, by payment method)
   - sales/{id}/receipt/ → Generate PDF receipt
   - customers/top_customers/ → Order by total_purchases DESC (limit 10)
   - customers/with_credits/ → Filter current_balance > 0
   - stock/movement_history/ → Filter by product, date range, movement_type
   - accounting/daily_summary/ → Get or create DailySummary for date
5. Pagination: PageNumberPagination, page_size=20
6. Optimize queries:
   - Sale: select_related('customer', 'user') + prefetch_related('items__product')
   - Product: select_related('category') + prefetch_related('packagings')
   - StockMovement: select_related('product', 'user')
   - CustomerCredit: select_related('customer', 'sale') + prefetch_related('payments')

Create views in api/v1/views/ organized by app.
Add comprehensive docstrings for API documentation.
```

---

### Prompt 4: JWT Authentication Endpoints
```
Implement JWT authentication endpoints for login/logout/refresh.

Requirements:
1. POST /api/v1/auth/login/
   - Input: username/email + password
   - Output: access_token, refresh_token, user data (role, name)
   - Log action to ActionLog with IP address
2. POST /api/v1/auth/logout/
   - Blacklist refresh token (install djangorestframework-simplejwt[blacklist])
   - Log logout action
3. POST /api/v1/auth/refresh/
   - Input: refresh_token
   - Output: new access_token
4. GET /api/v1/auth/me/
   - Return current authenticated user info

Add custom claim 'role' to JWT token payload.
Create in api/v1/auth/ folder.
```

---

## 🔥 PHASE 2B: Business Logic & Signals

### Prompt 5: Auto Stock Updates on Sale
```
Implement Django signals to automatically update stock when a sale is created.

Requirements:
1. Create apps/pos/signals.py
2. On Sale post_save (created=True):
   - For each SaleItem, create StockMovement with:
     - movement_type='exit'
     - reason='sale'
     - quantity from SaleItem.quantity
     - reference=sale.sale_number
     - user=sale.user (cashier)
     - product from SaleItem.product
   - StockMovement.save() already updates Stock.quantity (implemented in model)
3. Handle sale cancellation (status='cancelled'):
   - Create reverse 'entry' movements with reason='correction'
   - Only if sale was previously 'completed'
4. Handle sale refunds (status='refunded'):
   - Create 'entry' movements with reason='customer_return'
   - Update customer balance if payment was credit
5. Register signals in apps/pos/apps.py ready() method:
   ```python
   def ready(self):
       import apps.pos.signals
   ```
6. Add signal to create ActionLog entry for sale creation

Test cases:
- Create sale → verify stock decrements for each item
- Cancel sale → verify stock returns
- Test with products using different units (kg, liter, piece)

IMPORTANT: Use transaction.atomic() to ensure all StockMovements are created together.
```

---

### Prompt 6: Auto Customer Balance Updates
```
Implement signals for automatic customer statistics and balance tracking.

Note: CreditPayment.save() already updates balances (implemented in model).
This adds Sale creation tracking.

Requirements:
1. Create apps/customers/signals.py
2. On Sale post_save (created=True) with payment_method='credit':
   - Create CustomerCredit record:
     - customer=sale.customer
     - sale=sale (OneToOne)
     - original_amount=sale.total_amount - sale.amount_paid
     - remaining_amount=original_amount
     - status='pending'
   - Update Customer:
     - current_balance += remaining_amount
     - Validate: current_balance <= credit_limit (raise ValidationError if exceeded)
3. On any Sale post_save (created=True):
   - Update Customer (if customer is not None):
     - total_purchases += sale.total_amount
     - purchase_count += 1
     - If StoreSetting 'loyalty_program_enabled' == 'true':
       - loyalty_points += int(sale.total_amount / int(StoreSetting.get_setting('loyalty_points_rate', '1000')))
4. On Sale status change to 'cancelled' or 'refunded':
   - Reverse customer statistics
   - If has CustomerCredit, mark as 'paid' and reduce customer.current_balance
5. Register signals in apps/customers/apps.py ready() method

Test cases:
- Credit sale → CustomerCredit created, balance updated
- Cash sale → Only statistics updated
- Credit limit exceeded → ValidationError raised
- Cancelled sale → Statistics reversed

Use transaction.atomic() for data consistency.
```

---

### Prompt 7: Daily Summary Aggregation Job
```
Create management command to generate/update DailySummary records.

Requirements:
1. Create apps/accounting/management/commands/generate_daily_summary.py
2. Command syntax:
   - python manage.py generate_daily_summary [--date YYYY-MM-DD] [--backfill START END]
   - Default: generates for yesterday if no date provided
3. Aggregate data for the specified date:
   ```python
   # From Sales (status='completed')
   total_sales = Sale.objects.filter(created_at__date=date, status='completed').aggregate(Sum('total_amount'))
   
   # Payment methods breakdown
   total_cash = Sales.filter(payment_method='cash').aggregate(Sum('total_amount'))
   total_mobile_money = Sales.filter(payment_method='mobile_money').aggregate(Sum('total_amount'))
   total_card = Sales.filter(payment_method='card').aggregate(Sum('total_amount'))
   total_credit = Sales.filter(payment_method='credit').aggregate(Sum('total_amount'))
   
   # Cost of goods sold
   total_cost_of_goods = SaleItem.objects.filter(sale__created_at__date=date, sale__status='completed').aggregate(
       total=Sum(F('purchase_price') * F('quantity'))
   )
   
   # Credit collected (CreditPayment)
   credit_collected = CreditPayment.objects.filter(created_at__date=date).aggregate(Sum('amount'))
   
   # Expenses
   total_expenses = Expense.objects.filter(expense_date=date).aggregate(Sum('amount'))
   
   # Metrics
   gross_profit = total_sales - total_cost_of_goods
   net_profit = gross_profit - total_expenses
   number_of_sales = Sale.objects.filter(created_at__date=date, status='completed').count()
   number_of_customers = Sale.objects.filter(created_at__date=date, status='completed').values('customer').distinct().count()
   ```
4. Update or create DailySummary record (use update_or_create)
5. --backfill option:
   ```bash
   python manage.py generate_daily_summary --backfill 2025-01-01 2025-12-31
   ```
   Generates summaries for date range (useful for historical data)
6. Output:
   - "✅ Daily summary for 2025-12-04 created/updated"
   - "   Total Sales: 150,000 FCFA"
   - "   Net Profit: 45,000 FCFA"

Bonus: Set up Celery beat task to run automatically:
- Install celery, redis
- Create celery.py in stock_control/
- Schedule task to run daily at 00:30 (after midnight)
```

---

## 🔥 PHASE 2C: POS Frontend (Django Templates + HTMX)

### Prompt 8: POS Interface Template
```
Create a modern POS interface using Django templates, HTMX, and AlpineJS.

Requirements:
1. Create apps/pos/templates/pos/cashier.html
2. Layout (3-column responsive):
   - **Left Panel (40%)**: 
     - Barcode scanner input (autofocus, auto-submit on Enter)
     - Search box (product name/barcode, live search with HTMX)
     - Category filter tabs (All, then each Category.name)
     - Product grid (4 columns):
       - Product image (or placeholder)
       - Product name
       - Sale price (formatted: "2,500 FCFA")
       - Stock badge (green if in stock, red if low/out)
       - Click to add to cart
     - Show popular products (is_popular=True) first
   
   - **Center Panel (35%)**:
     - Cart header: "Panier (X articles)"
     - Cart items table:
       - Product name
       - Quantity (editable input with +/- buttons)
       - Unit price
       - Line total
       - Remove button (X icon)
     - Empty cart message if no items
     - Clear cart button
   
   - **Right Panel (25%)**:
     - Customer selector (dropdown with search, allow anonymous)
     - Discount section:
       - Toggle between % or fixed amount
       - Input field
     - Totals display:
       - Sous-total: X FCFA
       - Remise: -X FCFA
       - TVA: X FCFA
       - **Total: X FCFA** (large, bold)
     - Payment method radio buttons:
       - Espèces (Cash)
       - Mobile Money
       - Carte bancaire (Card)
       - Crédit (show customer credit limit)
     - Amount paid input (for cash, calculate change)
     - Change display: "Monnaie: X FCFA"
     - **Checkout button** (large, green, disabled if cart empty)

3. Features:
   - Barcode scanner: Autofocus input, beep sound on scan, auto-add to cart
   - HTMX endpoints:
     - hx-get="/pos/products/search/?q={query}" → Product grid
     - hx-post="/pos/cart/add/{product_id}/" → Add to cart
     - hx-post="/pos/cart/update/{item_id}/" → Update quantity
     - hx-delete="/pos/cart/remove/{item_id}/" → Remove item
     - hx-post="/pos/checkout/" → Complete sale
   - AlpineJS for:
     - Cart calculations (x-data with subtotal, discount, tax, total)
     - Change calculation (amount_paid - total)
     - Form validation
   - After checkout:
     - Show success modal with sale_number
     - Print receipt button (opens /pos/sales/{id}/receipt/ in new tab)
     - "Nouvelle vente" button to clear cart

4. Styling: 
   - Use TailwindCSS CDN
   - Color scheme: Blue primary (#3B82F6), Green success (#10B981), Red danger (#EF4444)
   - Large touch-friendly buttons (min 44px height)
   - Responsive for tablets (iPad landscape)

5. Views needed:
   - pos/cashier/ → Main POS view (GET)
   - pos/products/search/ → Product search (GET, returns HTML fragment)
   - pos/cart/add/ → Add to cart (POST, returns cart HTML)
   - pos/cart/update/ → Update cart (POST)
   - pos/cart/remove/ → Remove item (DELETE)
   - pos/checkout/ → Create Sale + SaleItems (POST)

6. Security:
   - @login_required decorator
   - Check user.role in ['admin', 'manager', 'cashier']
   - Store cart in session (request.session['cart'])

7. Language: All labels in French
   - "Caisse" (POS), "Panier" (Cart), "Total", "Espèces" (Cash), etc.
```

---

### Prompt 9: Inventory Management Interface
```
Create inventory management pages for stock_manager role.

Pages:
1. **apps/stock/templates/stock/dashboard.html** (Stock Overview)
   - Header: "Gestion de Stock"
   - Stats cards (row):
     - Total products (count)
     - Products in stock (Stock.quantity > 0)
     - Low stock alerts (quantity <= min_stock_threshold) - Red badge
     - Out of stock (quantity = 0) - Gray badge
   - Low stock alerts table:
     - Columns: Product, Category, Current Stock, Min Threshold, Actions
     - Red highlight if quantity = 0
     - Yellow if quantity <= min_threshold
     - "Réapprovisionner" button → Opens entry form with product pre-filled
   - Recent stock movements (last 20):
     - Columns: Date, Product, Type (Entry/Exit), Reason, Quantity, User
     - Color code: Green for entry, Red for exit
     - Filter by date range (last 7 days, 30 days, custom)

2. **apps/stock/templates/stock/entry.html** (Stock Entry)
   - Form title: "Entrée de Stock"
   - Product search field (autocomplete by name/barcode)
   - Fields:
     - Product (select with search)
     - Quantity (number, min=0.001)
     - Unit cost (FCFA)
     - Reason (dropdown): Purchase, Customer Return, Correction, Initial Stock, Transfer In, Other
     - Reference (text, e.g., "Invoice #12345")
     - Notes (textarea)
   - Batch entry option:
     - "Ajouter une ligne" button to add multiple products
     - Table with rows for multiple entries
     - "Enregistrer tout" button to save all at once
   - After save: Show success message, redirect to dashboard

3. **apps/stock/templates/stock/exit.html** (Manual Stock Exit)
   - Form title: "Sortie de Stock (Hors POS)"
   - Note: "Les ventes POS sont automatiquement enregistrées"
   - Same fields as entry but:
     - Reason dropdown: Manual Sale, Loss, Breakage, Expiration, Correction, Transfer Out, Other
     - Unit cost not required
   - Confirmation dialog: "Confirmer la sortie de X unités de [Product]?"

4. **apps/stock/templates/stock/history.html** (Movement History)
   - Title: "Historique des Mouvements"
   - Filters sidebar:
     - Product (autocomplete)
     - Date range (from/to with date picker)
     - Movement type (All, Entry, Exit)
     - Reason (dropdown with all reasons)
     - User (dropdown)
     - "Filtrer" button
   - Results table:
     - Columns: Date, Product, Type, Reason, Quantity, Unit Cost, Reference, User, Notes
     - Sortable columns (click header)
     - Pagination (50 per page)
   - Export buttons:
     - "Exporter Excel" → /stock/history/export/?[filters]
     - "Exporter PDF" → /stock/history/export-pdf/?[filters]

5. **apps/stock/templates/stock/product_detail.html** (Product Stock Detail)
   - Accessed from dashboard by clicking product name
   - Display:
     - Product info (name, category, barcode, current stock with gauge)
     - Stock valuation: quantity × purchase_price
     - Min stock threshold (visual indicator)
     - "Modifier le seuil" button (quick edit)
   - Movement history for this product only (last 50)
   - Chart: Stock level over time (last 30 days) using Chart.js

Styling:
- Use Bootstrap 5 or TailwindCSS
- French labels throughout
- Icons: Font Awesome or Heroicons
- Color scheme: Green for entry, Red for exit, Yellow for alerts

Views needed in apps/stock/views.py:
- DashboardView (GET)
- StockEntryView (GET/POST) with formset for batch
- StockExitView (GET/POST)
- MovementHistoryView (GET with filters)
- ProductDetailView (GET)
- Export views (CSV/Excel/PDF)

Security:
- @login_required
- Check user.role in ['admin', 'manager', 'stock_manager']
- Use Django messages for success/error feedback
```

---

### Prompt 10: Reports Dashboard
```
Create comprehensive reports dashboard for manager/admin roles.

Requirements:
1. **apps/reports/templates/reports/dashboard.html** (Main Dashboard)
   - Header: "Tableau de Bord"
   - Date range selector:
     - Quick filters: Aujourd'hui, 7 derniers jours, 30 derniers jours, Ce mois, Personnalisé
     - Custom date picker (from/to)
     - "Appliquer" button
   
   - **Key Metrics Cards** (4 columns, with % change vs previous period):
     - Total des Ventes (Total Sales):
       - Amount: "350,000 FCFA"
       - Change: "+12.5% vs previous period" (green up arrow)
       - Number of transactions below
     - Dépenses Totales (Total Expenses):
       - Amount with change indicator
     - Bénéfice Brut (Gross Profit):
       - Sales - Cost of Goods
       - Margin percentage below
     - Bénéfice Net (Net Profit):
       - Gross Profit - Expenses
       - Margin percentage
   
   - **Charts Section** (2 columns):
     - **Left**: Sales Trend (Line Chart)
       - Title: "Évolution des Ventes"
       - X-axis: Dates (daily if < 14 days, weekly if < 90 days, monthly otherwise)
       - Y-axis: Amount (FCFA)
       - Tooltip: Date, Sales amount, # of transactions
       - Use Chart.js
     
     - **Right**: Payment Methods (Pie Chart)
       - Title: "Répartition des Paiements"
       - Segments: Espèces, Mobile Money, Carte, Crédit
       - Percentages and amounts
       - Color coded
   
   - **Top Products Table** (below charts):
     - Title: "Top 10 Produits"
     - Columns: Rang, Produit, Quantité Vendue, Chiffre d'Affaires, Bénéfice
     - Sort by revenue DESC
     - Click row to see product detail report
   
   - **Expenses by Category** (Donut Chart):
     - Title: "Dépenses par Catégorie"
     - One segment per ExpenseCategory
     - Show amount and percentage

2. **apps/reports/templates/reports/sales_report.html** (Detailed Sales Report)
   - Title: "Rapport des Ventes"
   - Filters sidebar:
     - Date range
     - Customer (dropdown with search)
     - Cashier (User with role=cashier)
     - Payment method
     - Status
     - Minimum amount
     - "Filtrer" button
   
   - Sales table:
     - Columns: Date/Heure, N° de Vente, Client, Caissier, Articles, Total, Paiement, Statut
     - Click row to expand: Show all SaleItems in nested table
     - Color coding: Green for completed, Gray for cancelled, Yellow for refunded
     - Pagination (30 per page)
   
   - Summary footer:
     - Total ventes: X transactions
     - Montant total: X FCFA
     - Panier moyen: X FCFA (total / count)
   
   - Export buttons:
     - "Exporter Excel" → Downloads filtered results
     - "Exporter PDF" → Professional formatted report
     - "Imprimer" → Print view

3. **apps/reports/templates/reports/profit_report.html** (Profit Analysis)
   - Title: "Analyse de Rentabilité"
   - Date range filter
   
   - **Summary Cards**:
     - Chiffre d'Affaires (Total Sales)
     - Coût des Marchandises (Cost of Goods Sold)
     - Marge Brute (Gross Margin %)
     - Dépenses d'Exploitation (Expenses)
     - Bénéfice Net (Net Profit)
   
   - **Product-wise Profit Table**:
     - Columns: Produit, Catégorie, Qté Vendue, CA (Revenue), Coût Total, Bénéfice, Marge %
     - Formula: 
       - CA = SUM(SaleItem.quantity × SaleItem.unit_price)
       - Coût = SUM(SaleItem.quantity × SaleItem.purchase_price)
       - Bénéfice = CA - Coût
       - Marge % = (Bénéfice / CA) × 100
     - Sort by Bénéfice DESC (most profitable first)
     - Color code margin: Green > 30%, Yellow 15-30%, Red < 15%
     - Expandable rows to show individual sales
   
   - **Profit Trend Chart**:
     - Line chart showing daily/weekly profit over time
     - Two lines: Gross Profit (blue), Net Profit (green)
   
   - Export options: Excel, PDF

4. **apps/reports/templates/reports/customers_report.html** (Customer Analysis)
   - Title: "Rapport Clients"
   
   - Tabs:
     - **Top Clients**: Sort by total_purchases DESC
       - Table: Nom, Téléphone, Total Achats, Nombre d'Achats, Panier Moyen, Points Fidélité
       - Click to see customer detail page
     
     - **Clients avec Crédit**: Filter current_balance > 0
       - Table: Nom, Solde Dû, Date Dernière Vente, Jours en Retard, Actions
       - "Voir Détails" button → Shows all CustomerCredits
       - Color code: Red if overdue, Yellow if due soon
     
     - **Activité Récente**: Customers with sales in last 30 days
       - Last purchase date
       - Frequency (# of visits)

5. **apps/reports/templates/reports/expenses_report.html** (Expense Report)
   - Title: "Rapport des Dépenses"
   - Date range filter
   - Category filter
   
   - **Summary by Category**:
     - Pie chart (expenses by category)
     - Table with Category, Amount, % of Total, # of Transactions
   
   - **Detailed Expenses Table**:
     - Columns: Date, Catégorie, Description, Montant, Paiement, Fournisseur, Utilisateur
     - Filter and sort
     - Export Excel/PDF
   
   - **Recurring Expenses** section (is_recurring=True)
     - Separate table for tracking recurring costs

Views needed in apps/reports/views.py:
- DashboardView (GET with date_range parameter)
- SalesReportView (GET with filters)
- ProfitReportView (GET)
- CustomersReportView (GET with tab parameter)
- ExpensesReportView (GET)
- Export views for each report type

Security:
- @login_required
- Check user.role in ['admin', 'manager', 'accountant']
- Accountant has read-only access (no delete/edit buttons)

Dependencies:
- Chart.js for interactive charts
- DataTables.js for advanced table features (sort, search, pagination)
- Bootstrap DateRangePicker or Flatpickr for date selection
- Font Awesome icons
- Print CSS for printer-friendly versions

All text in French, currency formatted as "2 500 FCFA" (space thousands separator).
```

---

## 🔥 PHASE 2D: PDF & Excel Exports

### Prompt 11: Receipt PDF Generation
```
Generate PDF receipts for sales using ReportLab.

Requirements:
1. Install: pip install reportlab
2. Create apps/pos/utils/receipt_generator.py
3. Function: generate_receipt_pdf(sale_id, format='A4') → returns PDF bytes
   
4. Receipt Layout (A4 format):
   - **Header Section**:
     - Store logo (if StoreSetting 'store_logo' exists, use ImageReader)
     - Store name (from store_settings, centered, font size 18, bold)
     - Store address, phone, email (centered, font size 10)
     - Separator line
   
   - **Sale Information**:
     - "REÇU DE VENTE" (centered, bold, font size 14)
     - N° de Vente: [sale_number]
     - Date: [created_at formatted as DD/MM/YYYY HH:MM]
     - Caissier: [user.get_full_name()]
     - Client: [customer.name or "Client anonyme"]
     - Separator line
   
   - **Items Table**:
     - Headers: Produit | Qté | P.U. | Total
     - Column widths: 50% | 15% | 15% | 20%
     - Rows: For each SaleItem
       - product_name
       - quantity (formatted: "2.500" for decimals)
       - unit_price (formatted: "1 500 FCFA")
       - total_price (formatted)
     - Separator line after items
   
   - **Totals Section** (right-aligned):
     - Sous-total: [subtotal] FCFA
     - Remise: -[discount_amount] FCFA (only if > 0)
     - TVA: [tax_amount] FCFA (only if > 0)
     - **TOTAL: [total_amount] FCFA** (bold, larger font)
     - Montant payé: [amount_paid] FCFA
     - Monnaie: [change_amount] FCFA (only if payment_method != 'credit')
     - Mode de paiement: [payment_method translated to French]
   
   - **Footer Section**:
     - Receipt footer message (from StoreSetting 'receipt_footer')
     - Barcode of sale_number (use reportlab.graphics.barcode)
     - "Document généré le [current_datetime]"
     - Website (if in store_settings)
   
5. Thermal Printer Format (80mm width):
   - Simplified layout for small paper
   - Same sections but:
     - Smaller fonts (8-10pt)
     - No logo (optional small icon)
     - Narrower columns
     - QR code instead of barcode (sale_number)
   - Function parameter: format='thermal'

6. Endpoint: GET /api/v1/sales/{id}/receipt/?format=A4
   - Returns PDF file with Content-Type: application/pdf
   - Filename: Recu_{sale_number}.pdf
   - Add format parameter: A4 or thermal

7. Add to apps/pos/templates/pos/cashier.html:
   - After successful checkout, show modal with:
     - "Vente enregistrée: {sale_number}"
     - "Imprimer le reçu" button → Opens receipt URL in new tab
     - "Envoyer par email" button (if customer has email)
   
8. Integration:
   - Create view: SaleReceiptView(DetailView)
   - URL: path('sales/<int:pk>/receipt/', SaleReceiptView.as_view(), name='sale-receipt')
   - Permission: User must be cashier/manager/admin
   - Log receipt generation in ActionLog

Format numbers:
- Use French locale: 1 500,50 FCFA (space as thousands separator, comma for decimals)
- Helper function: format_currency(amount) → "1 500,50 FCFA"

Fonts:
- Use Helvetica (built-in ReportLab font)
- Or embed custom font (e.g., Roboto) for better look

Test with:
- Sale with multiple items
- Sale with discount
- Sale with tax
- Credit sale (no change)
- Long product names (wrap text)
```

---

### Prompt 12: Excel Reports Export
```
Generate Excel reports using openpyxl with professional formatting.

Requirements:
1. Install: pip install openpyxl
2. Create apps/reports/utils/excel_generator.py

3. **Report Functions**:

   A. **sales_report(start_date, end_date, filters=None)** → Workbook
      - Sheet 1: "Résumé" (Summary)
        - Période: [start_date] à [end_date]
        - Nombre de ventes: X
        - Chiffre d'affaires: X FCFA
        - Panier moyen: X FCFA
        - Breakdown by payment method (table)
      
      - Sheet 2: "Ventes Détaillées" (Detailed Sales)
        - Headers: Date, N° Vente, Client, Caissier, Sous-total, Remise, TVA, Total, Paiement, Statut
        - One row per sale
        - Filters applied if provided (customer, cashier, payment_method)
      
      - Sheet 3: "Articles Vendus" (Items Sold)
        - Headers: Date, N° Vente, Produit, Catégorie, Qté, P.U., P.A., Total, Bénéfice
        - One row per SaleItem
        - Include profit column (unit_price - purchase_price) × quantity
   
   B. **inventory_report()** → Workbook
      - Sheet 1: "Stock Actuel" (Current Stock)
        - Headers: Produit, Catégorie, Code-barres, Qté en Stock, Seuil Min, Statut, Coût Unitaire, Valeur Totale
        - Statut: "En stock", "Stock faible", "Rupture"
        - Valeur = quantity × purchase_price
        - Total row at bottom
        - Conditional formatting: Red for rupture, Yellow for low stock
      
      - Sheet 2: "Produits Populaires" (Popular Products)
        - Only is_popular=True products
        - Current stock for POS quick access
   
   C. **profit_report(start_date, end_date)** → Workbook
      - Sheet 1: "Rentabilité par Produit" (Product Profitability)
        - Headers: Produit, Catégorie, Qté Vendue, CA, Coût Total, Bénéfice, Marge %
        - Sorted by Bénéfice DESC
        - Conditional formatting: Marge % (green > 30%, yellow 15-30%, red < 15%)
      
      - Sheet 2: "Résumé Financier" (Financial Summary)
        - Key metrics:
          - Chiffre d'affaires total
          - Coût des marchandises
          - Bénéfice brut
          - Dépenses
          - Bénéfice net
          - Marge brute %
          - Marge nette %
   
   D. **expense_report(start_date, end_date)** → Workbook
      - Sheet 1: "Dépenses par Catégorie" (Expenses by Category)
        - Headers: Catégorie, Montant, Nombre, Montant Moyen, % du Total
        - Total row
      
      - Sheet 2: "Dépenses Détaillées" (Detailed Expenses)
        - Headers: Date, Catégorie, Description, Montant, Paiement, Fournisseur, Référence, Utilisateur
        - One row per expense
        - Filter by date range
   
   E. **customer_report()** → Workbook
      - Sheet 1: "Top Clients" (Top Customers)
        - Headers: Rang, Client, Téléphone, Total Achats, Nb Achats, Panier Moyen, Solde Crédit, Points Fidélité
        - Sort by total_purchases DESC
        - Top 100 customers
      
      - Sheet 2: "Clients avec Crédit" (Customers with Credit)
        - Headers: Client, Téléphone, Solde Dû, Limite Crédit, % Utilisé, Dernière Vente, Jours en Retard
        - Only current_balance > 0
        - Sort by current_balance DESC

4. **Excel Formatting Features**:
   - Auto-adjust column widths: `column.width = max(len(str(cell.value)) for cell in column) + 2`
   - Header row:
     - Bold font (Font(bold=True))
     - Background color (PatternFill with light blue)
     - Border (Border with thin lines)
     - Alignment (Alignment(horizontal='center'))
   - Freeze header row: `sheet.freeze_panes = 'A2'`
   - Number formatting:
     - Currency: `cell.number_format = '#,##0.00 "FCFA"'`
     - Percentage: `cell.number_format = '0.00%'`
     - Date: `cell.number_format = 'DD/MM/YYYY'`
   - Total row:
     - Bold font
     - Light gray background
     - Top border (double line)
   - Conditional formatting (openpyxl.formatting.rule):
     - Stock status colors
     - Profit margin colors
     - Overdue credits (red)

5. **API Endpoints**:
   - GET /api/v1/reports/sales/export/?start_date=X&end_date=X&format=excel
   - GET /api/v1/reports/inventory/export/?format=excel
   - GET /api/v1/reports/profit/export/?start_date=X&end_date=X&format=excel
   - GET /api/v1/reports/expenses/export/?start_date=X&end_date=X&format=excel
   - GET /api/v1/reports/customers/export/?format=excel

6. **Views** (apps/reports/views.py):
   ```python
   @login_required
   def export_sales_report(request):
       start_date = request.GET.get('start_date')
       end_date = request.GET.get('end_date')
       # Parse dates, validate
       workbook = sales_report(start_date, end_date)
       response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
       response['Content-Disposition'] = f'attachment; filename=Rapport_Ventes_{start_date}_{end_date}.xlsx'
       workbook.save(response)
       return response
   ```

7. **Integration**:
   - Add "Exporter Excel" buttons in all report pages
   - Use HTMX or regular anchor tags
   - Show loading spinner during export
   - Log export action in ActionLog

8. **Permissions**:
   - admin, manager, accountant can export
   - cashier, stock_manager cannot export (sensitive data)

Test cases:
- Empty data (show "Aucune donnée" message)
- Large datasets (1000+ rows) - ensure performance
- Special characters in product names (encoding)
- Date range validation
- Filter combinations

Helper functions needed:
- format_currency(amount) → "1 500,50 FCFA"
- format_date(date) → "04/12/2025"
- format_percentage(value) → "15.5%"
- apply_header_style(worksheet, row_num)
- apply_total_row_style(worksheet, row_num)
```

---

## 🔥 PHASE 2E: Testing & Optimization

### Prompt 13: Write Unit Tests
```
Create comprehensive unit tests for models and API with 80%+ coverage.

Requirements:
1. Install test dependencies:
   ```bash
   pip install factory-boy faker coverage django-coverage-plugin
   ```

2. **Test Structure**:
   ```
   apps/
   ├── accounts/tests/
   │   ├── __init__.py
   │   ├── factories.py      # Factory classes
   │   ├── test_models.py
   │   └── test_api.py
   ├── products/tests/
   │   ├── factories.py
   │   ├── test_models.py
   │   └── test_api.py
   └── [other apps same structure]
   ```

3. **Factories** (using factory_boy):
   ```python
   # apps/accounts/tests/factories.py
   import factory
   from apps.accounts.models import User
   
   class UserFactory(factory.django.DjangoModelFactory):
       class Meta:
           model = User
       
       username = factory.Sequence(lambda n: f'user{n}')
       email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
       first_name = factory.Faker('first_name')
       last_name = factory.Faker('last_name')
       role = 'cashier'
       password = factory.PostGenerationMethodCall('set_password', 'testpass123')
   
   class AdminFactory(UserFactory):
       role = 'admin'
       is_staff = True
       is_superuser = True
   ```
   
   Create factories for all 17 models.

4. **Model Tests** (apps/*/tests/test_models.py):
   
   Test for each model:
   - Creation with valid data
   - String representation (__str__)
   - Unique constraints (barcode, email, sale_number)
   - Foreign key relationships
   - Properties (profit_margin, is_low_stock, has_outstanding_credit)
   - Model methods (generate_sale_number, get_setting, set_setting)
   - Validation errors (negative amounts, price constraints)
   
   Example:
   ```python
   # apps/products/tests/test_models.py
   from django.test import TestCase
   from apps.products.models import Product, Category
   from .factories import ProductFactory, CategoryFactory
   
   class ProductModelTest(TestCase):
       def setUp(self):
           self.category = CategoryFactory()
           self.product = ProductFactory(category=self.category)
       
       def test_product_creation(self):
           self.assertIsNotNone(self.product.id)
           self.assertEqual(self.product.category, self.category)
       
       def test_profit_margin_calculation(self):
           product = ProductFactory(purchase_price=100, sale_price=150)
           self.assertEqual(product.profit_margin, 50.0)
       
       def test_barcode_unique(self):
           ProductFactory(barcode='12345')
           with self.assertRaises(IntegrityError):
               ProductFactory(barcode='12345')
       
       def test_string_representation(self):
           self.assertIn(self.product.name, str(self.product))
   ```

5. **Signal Tests**:
   ```python
   # apps/pos/tests/test_signals.py
   class SaleSignalTest(TestCase):
       def test_stock_decrements_on_sale(self):
           product = ProductFactory()
           stock = StockFactory(product=product, quantity=100)
           
           sale = SaleFactory()
           SaleItemFactory(sale=sale, product=product, quantity=10)
           
           stock.refresh_from_db()
           self.assertEqual(stock.quantity, 90)
       
       def test_customer_balance_updates_on_credit_sale(self):
           customer = CustomerFactory(current_balance=0)
           sale = SaleFactory(
               customer=customer,
               payment_method='credit',
               total_amount=5000
           )
           
           customer.refresh_from_db()
           self.assertEqual(customer.current_balance, 5000)
   ```

6. **API Tests** (apps/*/tests/test_api.py):
   
   Use Django REST Framework's APITestCase:
   ```python
   from rest_framework.test import APITestCase, APIClient
   from rest_framework import status
   
   class ProductAPITest(APITestCase):
       def setUp(self):
           self.client = APIClient()
           self.admin = AdminFactory()
           self.cashier = UserFactory(role='cashier')
           self.product = ProductFactory()
       
       def test_list_products_unauthenticated(self):
           response = self.client.get('/api/v1/products/')
           self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
       
       def test_list_products_authenticated(self):
           self.client.force_authenticate(user=self.admin)
           response = self.client.get('/api/v1/products/')
           self.assertEqual(response.status_code, status.HTTP_200_OK)
           self.assertGreaterEqual(len(response.data['results']), 1)
       
       def test_create_product_admin(self):
           self.client.force_authenticate(user=self.admin)
           data = {
               'name': 'New Product',
               'category': CategoryFactory().id,
               'unit': 'piece',
               'purchase_price': '100.00',
               'sale_price': '150.00',
           }
           response = self.client.post('/api/v1/products/', data)
           self.assertEqual(response.status_code, status.HTTP_201_CREATED)
       
       def test_create_product_cashier_forbidden(self):
           self.client.force_authenticate(user=self.cashier)
           data = {...}
           response = self.client.post('/api/v1/products/', data)
           self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
       
       def test_product_search(self):
           self.client.force_authenticate(user=self.admin)
           ProductFactory(name='Coca Cola')
           response = self.client.get('/api/v1/products/?search=coca')
           self.assertEqual(len(response.data['results']), 1)
       
       def test_low_stock_action(self):
           self.client.force_authenticate(user=self.admin)
           product = ProductFactory(min_stock_threshold=10)
           StockFactory(product=product, quantity=5)
           response = self.client.get('/api/v1/products/low_stock/')
           self.assertIn(product.id, [p['id'] for p in response.data])
   ```

7. **Authentication Tests**:
   ```python
   # api/v1/tests/test_auth.py
   class AuthAPITest(APITestCase):
       def test_login_success(self):
           user = UserFactory(username='testuser')
           response = self.client.post('/api/v1/auth/login/', {
               'username': 'testuser',
               'password': 'testpass123'
           })
           self.assertEqual(response.status_code, status.HTTP_200_OK)
           self.assertIn('access', response.data)
           self.assertIn('refresh', response.data)
       
       def test_login_invalid_credentials(self):
           response = self.client.post('/api/v1/auth/login/', {
               'username': 'wrong',
               'password': 'wrong'
           })
           self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
       
       def test_token_refresh(self):
           user = UserFactory()
           login_response = self.client.post('/api/v1/auth/login/', {...})
           refresh_token = login_response.data['refresh']
           
           response = self.client.post('/api/v1/auth/refresh/', {
               'refresh': refresh_token
           })
           self.assertEqual(response.status_code, status.HTTP_200_OK)
           self.assertIn('access', response.data)
   ```

8. **Permission Tests** for all roles:
   - Admin: Full CRUD on all endpoints
   - Manager: CRUD except users
   - Stock_manager: Only stock operations
   - Cashier: Only POS + read customers
   - Accountant: Read-only all

9. **Coverage Configuration**:
   Create `.coveragerc`:
   ```ini
   [run]
   source = .
   omit =
       */migrations/*
       */tests/*
       */venv/*
       */virtualenv/*
       */.venv/*
       manage.py
       */settings.py
   
   [report]
   precision = 2
   show_missing = True
   ```

10. **Running Tests**:
    ```bash
    # Run all tests
    python manage.py test
    
    # Run specific app
    python manage.py test apps.products
    
    # Run with coverage
    coverage run --source='.' manage.py test
    coverage report
    coverage html  # Generate HTML report in htmlcov/
    
    # Run fast (parallel)
    python manage.py test --parallel
    ```

11. **Test Database**:
    Configure test database in settings.py:
    ```python
    if 'test' in sys.argv:
        DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    ```

12. **CI/CD Integration** (GitHub Actions):
    Create `.github/workflows/tests.yml`:
    ```yaml
    name: Tests
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v2
          - name: Set up Python
            uses: actions/setup-python@v2
            with:
              python-version: 3.13
          - name: Install dependencies
            run: pip install -r requirements.txt
          - name: Run tests
            run: python manage.py test --parallel
          - name: Coverage
            run: |
              coverage run manage.py test
              coverage report --fail-under=80
    ```

Goal: Achieve 80%+ test coverage for confidence in code quality.
```

---

### Prompt 14: Database Optimization
```
Optimize database queries to prevent N+1 problems.

Tasks:
1. Add select_related() for all ForeignKey fetches:
   - Sale.objects.select_related('customer', 'user')
   - Product.objects.select_related('category')
2. Add prefetch_related() for reverse FKs:
   - Sale.objects.prefetch_related('items__product')
   - Customer.objects.prefetch_related('credits', 'sales')
3. Create custom QuerySet managers with optimization built-in:
   - SaleQuerySet.with_details()
   - ProductQuerySet.with_stock_info()
4. Add database indexes for common queries:
   - Index on (created_at, status) for Sales
   - Index on (customer_id, status) for CustomerCredits
5. Use django-debug-toolbar to identify slow queries
6. Install django-silk for profiling:
   - pip install django-silk
   - Add 'silk' to INSTALLED_APPS
   - Add middleware
   - Access profiling at /silk/
7. Database connection pooling:
   - pip install django-db-connection-pool
   - Configure in settings.py
8. Cache frequent queries:
   - Install django-cacheops or use Django's built-in cache
   - Cache Category list (rarely changes)
   - Cache StoreSetting values
   - Invalidate cache on updates

Run: python manage.py check --deploy
```

---

### Prompt 15: Production Readiness
```
Prepare the app for production deployment.

Tasks:
1. Security:
   - Change SECRET_KEY to env variable (already done)
   - Set DEBUG=False in production
   - Configure ALLOWED_HOSTS from env
   - Add security middleware:
     - django-ratelimit for API rate limiting
     - CSRF protection for forms
     - XSS protection headers
   - Enable HTTPS redirects (SECURE_SSL_REDIRECT)
   - Set secure cookies (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
   - Add HSTS headers

2. Static files:
   - Configure STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
   - Run: python manage.py collectstatic
   - Set up WhiteNoise for serving:
     ```python
     MIDDLEWARE = [
         'whitenoise.middleware.WhiteNoiseMiddleware',
         ...
     ]
     STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
     ```

3. Database:
   - Use environment variables for all DB credentials
   - Add database connection pooling
   - Configure automated backups (mysqldump cron job)
   - Enable MySQL slow query log for debugging

4. Logging:
   - Configure Django logging to file:
     ```python
     LOGGING = {
         'version': 1,
         'handlers': {
             'file': {
                 'class': 'logging.FileHandler',
                 'filename': 'logs/django.log',
             },
         },
         'loggers': {
             'django': {
                 'handlers': ['file'],
                 'level': 'WARNING',
             },
         },
     }
     ```
   - Optional: Log errors to Sentry (pip install sentry-sdk)

5. Environment files:
   - Create .env.production template:
     ```
     DEBUG=False
     SECRET_KEY=<generate-new-key>
     ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
     DB_NAME=stock_control_pos
     DB_USER=produser
     DB_PASSWORD=<secure-password>
     DB_HOST=localhost
     DB_PORT=3306
     ```
   - Document required env variables in README.md

6. Deployment options:

   A. Docker deployment:
      - Create Dockerfile:
        ```dockerfile
        FROM python:3.13-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY . .
        RUN python manage.py collectstatic --noinput
        EXPOSE 8000
        CMD ["gunicorn", "stock_control.wsgi:application", "--bind", "0.0.0.0:8000"]
        ```
      - Create docker-compose.yml (app + nginx + mysql)
      - Add health check endpoint: GET /health/

   B. VPS deployment:
      - Install: gunicorn, supervisor
      - Configure supervisor to manage gunicorn process
      - Set up nginx as reverse proxy
      - Configure SSL with Let's Encrypt (certbot)

   C. PaaS deployment:
      - Railway: Add railway.json configuration
      - DigitalOcean App Platform: Add app.yaml
      - AWS Elastic Beanstalk: Add .ebextensions/

7. Performance:
   - Install gunicorn: pip install gunicorn
   - Configure workers: gunicorn -w 4 stock_control.wsgi
   - Add gevent for async workers (pip install gevent)

8. Monitoring:
   - Add health check endpoint at /health/
   - Optional: Set up uptime monitoring (UptimeRobot, Pingdom)
   - Set up error alerting (email on 500 errors)

9. Final checklist:
   - [ ] python manage.py check --deploy (fix all warnings)
   - [ ] python manage.py migrate (ensure migrations are applied)
   - [ ] Create superuser for production admin
   - [ ] Test all critical workflows
   - [ ] Backup database before going live
   - [ ] Configure domain and DNS
   - [ ] Set up SSL certificate
   - [ ] Test error handling and 404/500 pages

Target platforms: DigitalOcean Droplet, Railway, or AWS.
```

---

## 🔥 BONUS: Additional Features

### Prompt 16: Email Notifications
```
Add email notifications for important events.

Requirements:
1. Configure email backend in settings.py:
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
   EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
   EMAIL_USE_TLS = True
   EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
   EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
   DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com')
   ```

2. Create apps/core/utils/email_service.py:
   - send_receipt_email(sale_id, customer_email)
   - send_low_stock_alert(product_ids, to_emails)
   - send_daily_summary_email(date, to_emails)
   - send_credit_reminder(customer_id)
   - send_overdue_credit_alert(customer_id)

3. Email templates (HTML + plain text):
   - templates/emails/receipt.html
   - templates/emails/low_stock_alert.html
   - templates/emails/daily_summary.html
   - templates/emails/credit_reminder.html
   - Use Django's template system with context

4. Integrate with signals:
   - After sale creation: Send receipt if customer has email
   - Daily job: Send low stock alerts to manager
   - Daily job: Send summary report to admin/manager

5. Celery tasks for async email sending:
   - tasks.send_email_async.delay(subject, body, to_emails)
   - Don't block request/response cycle

6. Store email settings in StoreSetting:
   - email_notifications_enabled (true/false)
   - low_stock_alert_emails (comma-separated)
   - daily_summary_emails (comma-separated)

Test: python manage.py shell -c "from apps.core.utils.email_service import send_receipt_email; send_receipt_email(1, 'test@example.com')"
```

---

### Prompt 17: Barcode Scanner Integration
```
Add support for USB barcode scanners in POS interface.

Requirements:
1. Barcode input field in POS:
   - Autofocus on page load
   - Hidden or minimal styling
   - Keyboard input handler

2. JavaScript barcode detection:
   ```javascript
   let barcodeBuffer = '';
   let lastKeyTime = Date.now();
   
   document.addEventListener('keypress', (e) => {
       const currentTime = Date.now();
       if (currentTime - lastKeyTime > 50) {
           barcodeBuffer = '';  // Reset if delay too long (human typing)
       }
       lastKeyTime = currentTime;
       
       if (e.key === 'Enter' && barcodeBuffer.length > 3) {
           // Barcode complete, search product
           searchProductByBarcode(barcodeBuffer);
           barcodeBuffer = '';
       } else {
           barcodeBuffer += e.key;
       }
   });
   ```

3. Product search by barcode:
   - Check Product.barcode first
   - Then check ProductPackaging.barcode
   - If packaging, add quantity_per_unit to cart
   - Show error if not found (beep sound)

4. Sound feedback:
   - Success beep: Product found and added
   - Error beep: Barcode not found
   - Use Web Audio API or <audio> element

5. Support common barcode formats:
   - EAN-13 (13 digits)
   - UPC-A (12 digits)
   - Code 128 (variable length)
   - QR codes (for advanced features)

6. Testing mode:
   - Button to enable "Test Mode" (simulate scanner with keyboard)
   - Generate test barcodes for products

7. Multiple scanner support:
   - Handheld USB scanner
   - Bluetooth scanner
   - Mobile camera scanner (optional with QuaggaJS library)

Integration: Add to apps/pos/templates/pos/cashier.html
```

---

### Prompt 18: Backup & Restore System
```
Implement automated database backup and restore functionality.

Requirements:
1. Create apps/core/management/commands/backup_database.py:
   ```bash
   python manage.py backup_database [--output /path/to/backup.sql]
   ```

2. MySQL backup using mysqldump:
   ```python
   import subprocess
   import os
   from datetime import datetime
   
   def backup_database():
       timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
       filename = f'backup_{timestamp}.sql'
       backup_path = os.path.join(settings.BACKUP_DIR, filename)
       
       command = [
           'mysqldump',
           f'--user={settings.DATABASES["default"]["USER"]}',
           f'--password={settings.DATABASES["default"]["PASSWORD"]}',
           f'--host={settings.DATABASES["default"]["HOST"]}',
           settings.DATABASES["default"]["NAME"],
           f'--result-file={backup_path}'
       ]
       
       subprocess.run(command, check=True)
       return backup_path
   ```

3. Automatic scheduled backups:
   - Celery beat task (if using Celery)
   - Or cron job: `0 2 * * * cd /path && python manage.py backup_database`
   - Frequency from StoreSetting 'backup_frequency' (daily, weekly)

4. Backup retention:
   - Keep last 7 daily backups
   - Keep last 4 weekly backups
   - Keep last 12 monthly backups
   - Auto-delete old backups

5. Backup to cloud storage (optional):
   - AWS S3
   - Google Cloud Storage
   - Dropbox
   - Install: pip install boto3 (for S3)

6. Restore command:
   ```bash
   python manage.py restore_database --file /path/to/backup.sql
   ```
   - Confirm with user (dangerous operation)
   - Create backup before restore
   - Use mysql command to import

7. Admin interface:
   - apps/core/templates/admin/backup_restore.html
   - List available backups (filename, size, date)
   - Download button
   - Restore button (with confirmation)
   - Manual backup trigger button

8. Backup verification:
   - Test restore in isolated environment
   - Check backup file integrity (file size, SQL syntax)

9. Backup notifications:
   - Email admin after successful backup
   - Alert if backup fails

Configuration in settings.py:
```python
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
BACKUP_RETENTION_DAYS = 30
BACKUP_TO_CLOUD = os.getenv('BACKUP_TO_CLOUD', 'false') == 'true'
```

Security: Ensure backup files are not web-accessible (outside MEDIA_ROOT).
```

---

### Prompt 19: Multi-Store Support
```
Extend the system to support multiple store locations (optional for future).

Requirements:
1. Create apps/core/models.py:
   ```python
   class Store(models.Model):
       name = models.CharField(max_length=200)
       code = models.CharField(max_length=20, unique=True)
       address = models.TextField()
       phone = models.CharField(max_length=20)
       is_active = models.BooleanField(default=True)
       created_at = models.DateTimeField(auto_now_add=True)
   ```

2. Add store_id to relevant models:
   - Product (stock per store)
   - Sale (which store made the sale)
   - Stock (one stock record per product per store)
   - CashRegisterSession (per store)

3. Update Stock model:
   ```python
   class Stock(models.Model):
       store = models.ForeignKey('core.Store', on_delete=models.CASCADE)
       product = models.ForeignKey(Product, on_delete=models.CASCADE)
       quantity = models.DecimalField(...)
       
       class Meta:
           unique_together = [['store', 'product']]
   ```

4. User assignment to stores:
   - Add store field to User model
   - Users can access only their assigned store
   - Admin/Manager can access all stores

5. Store selector in UI:
   - Dropdown in navbar (for multi-store users)
   - Store store_id in session
   - Filter all queries by current store

6. Inter-store transfers:
   - New model: StockTransfer(from_store, to_store, product, quantity)
   - Create exit movement at source, entry at destination
   - Approval workflow for managers

7. Reports per store:
   - Add store filter to all reports
   - Cross-store comparison report

8. Database considerations:
   - Use Django's multi-tenancy packages (django-tenant-schemas)
   - Or simple store_id filtering

9. Migration strategy:
   - Add Store model
   - Create default store "Main Store"
   - Migrate existing data to default store
   - Then allow adding more stores

Note: This is a significant architectural change. Start simple with single store, add later if needed.
```

---

### Prompt 20: Mobile App API Enhancements
```
Enhance API for mobile POS app (React Native, Flutter, etc.)

Requirements:
1. Offline mode support:
   - Sync endpoints:
     - POST /api/v1/sync/products/ (get products updated since timestamp)
     - POST /api/v1/sync/sales/ (upload offline sales)
     - POST /api/v1/sync/stock/ (get current stock)
   - Use timestamps and version numbers for conflict resolution

2. Optimized endpoints for mobile:
   - GET /api/v1/pos/products/?minimal=true (only id, name, price, stock)
   - GET /api/v1/pos/categories/ (categories for filtering)
   - POST /api/v1/pos/quick-sale/ (create sale in one request)

3. Image optimization:
   - Generate thumbnails for product images
   - Use PIL/Pillow to create small (100x100), medium (300x300) sizes
   - Add thumbnail URLs in serializer

4. Push notifications:
   - Install: pip install fcm-django
   - Send low stock alerts to mobile
   - Send new sale notifications to managers
   - Customer credit reminders

5. QR code generation:
   - Generate QR for sales (for customer verification)
   - Generate QR for products (for quick scanning)
   - Use: pip install qrcode

6. Fingerprint/PIN for cashier login:
   - Add PIN field to User model
   - Endpoint: POST /api/v1/auth/login-pin/ (username + PIN)
   - Faster than password for mobile

7. Receipt printing from mobile:
   - Bluetooth printer support (handled by mobile app)
   - API returns receipt HTML or raw text format
   - GET /api/v1/sales/{id}/receipt/?format=text

8. Dashboard widgets for mobile:
   - Today's sales summary
   - Top 5 products
   - Low stock count
   - Single endpoint: GET /api/v1/dashboard/

9. Pagination for mobile:
   - Cursor-based pagination (more efficient)
   - Smaller page sizes (10-15 items)

10. API versioning:
    - /api/v1/ for current
    - /api/v2/ for future changes
    - Maintain backward compatibility

Documentation: Use drf-spectacular to generate OpenAPI spec for mobile team.
```

---

### Prompt 21: ActionLog Integration
```
Implement comprehensive audit logging using the ActionLog model.

Requirements:
1. Create apps/core/utils/audit_logger.py:
   ```python
   from apps.accounts.models import ActionLog
   import json
   
   def log_action(user, action_type, entity_type, entity_id=None, 
                  description=None, old_value=None, new_value=None, ip_address=None):
       ActionLog.objects.create(
           user=user,
           action_type=action_type,
           entity_type=entity_type,
           entity_id=entity_id,
           description=description,
           old_value=json.dumps(old_value) if old_value else None,
           new_value=json.dumps(new_value) if new_value else None,
           ip_address=ip_address
       )
   ```

2. Create middleware for IP tracking:
   - apps/core/middleware/audit_middleware.py
   - Store request.user and IP in thread-local storage
   - Access in signals and views

3. Log these events:
   - login/logout (already tracked by Django signals)
   - User create/update/delete (especially role changes)
   - Product price changes (track old_value, new_value)
   - Large stock movements (> configurable threshold from StoreSetting)
   - Customer credit limit changes
   - Customer balance adjustments
   - Expense deletion/modification
   - Sale cancellation/refund
   - Cash register session close (record difference)

4. Signal implementations:
   ```python
   # apps/products/signals.py
   @receiver(pre_save, sender=Product)
   def track_product_changes(sender, instance, **kwargs):
       if instance.pk:
           old = Product.objects.get(pk=instance.pk)
           if old.sale_price != instance.sale_price:
               log_action(
                   user=get_current_user(),
                   action_type='update',
                   entity_type='product',
                   entity_id=instance.pk,
                   description=f'Price changed for {instance.name}',
                   old_value={'sale_price': str(old.sale_price)},
                   new_value={'sale_price': str(instance.sale_price)}
               )
   ```

5. Admin enhancements:
   - Add ActionLog to admin (read-only)
   - Filter by action_type, entity_type, user, date
   - Search by description
   - Show old/new values in detail view

6. API endpoints:
   - GET /api/v1/audit-logs/ (admin only)
   - Filter by entity_type, date range, user
   - Pagination (50 per page)

7. Retention policy:
   - Management command: python manage.py cleanup_audit_logs --days 365
   - Delete logs older than 1 year (configurable)
   - Optional: Archive to separate table before deletion

8. Reports:
   - User activity report (actions per user per day)
   - Price change history for products
   - Stock movement audit trail
   - Security audit (failed logins if tracked)

Integration: Add audit logging to all CRUD operations without breaking existing functionality.
```

---

### Prompt 22: Localization & Multi-Language
```
Add full French localization and prepare for multi-language support.

Requirements:
1. Configure Django i18n:
   ```python
   # settings.py
   LANGUAGE_CODE = 'fr'
   USE_I18N = True
   USE_L10N = True
   
   LANGUAGES = [
       ('fr', 'Français'),
       ('en', 'English'),
   ]
   
   LOCALE_PATHS = [
       os.path.join(BASE_DIR, 'locale'),
   ]
   
   # Add middleware
   MIDDLEWARE = [
       'django.middleware.locale.LocaleMiddleware',
       ...
   ]
   ```

2. Create translation files:
   ```bash
   mkdir -p locale/fr/LC_MESSAGES
   python manage.py makemessages -l fr
   ```

3. Mark all user-facing strings:
   - Views: from django.utils.translation import gettext_lazy as _
   - Templates: {% load i18n %} and {% trans "text" %}
   - Model verbose_name: verbose_name=_("Product")
   - Form labels and error messages
   - Email templates
   - PDF reports

4. Key French translations:
   ```
   # locale/fr/LC_MESSAGES/django.po
   msgid "Product"
   msgstr "Produit"
   
   msgid "Sale"
   msgstr "Vente"
   
   msgid "Customer"
   msgstr "Client"
   
   msgid "Stock"
   msgstr "Stock"
   
   msgid "Total"
   msgstr "Total"
   
   msgid "Cash"
   msgstr "Espèces"
   
   msgid "Mobile Money"
   msgstr "Mobile Money"
   
   msgid "Credit"
   msgstr "Crédit"
   
   msgid "Payment Method"
   msgstr "Mode de Paiement"
   
   # ... complete translations
   ```

5. Compile translations:
   ```bash
   python manage.py compilemessages
   ```

6. Number and currency formatting:
   ```python
   # Use django.contrib.humanize
   INSTALLED_APPS += ['django.contrib.humanize']
   
   # In templates: {% load humanize %}
   # {{ amount|intcomma }} → 1,500
   
   # Custom filter for FCFA:
   @register.filter
   def fcfa(value):
       return f"{value:,.0f} FCFA".replace(',', ' ')
   ```

7. Date formatting:
   ```python
   DATE_FORMAT = 'd/m/Y'  # French format: 04/12/2025
   DATETIME_FORMAT = 'd/m/Y H:i'
   SHORT_DATE_FORMAT = 'd/m/Y'
   ```

8. User language preference:
   - Add language field to User model (optional)
   - Or use session/cookie to store preference
   - Language switcher in UI

9. Test all interfaces in French:
   - Admin panel
   - POS interface
   - Reports
   - Email templates
   - PDF receipts
   - Error messages

Goal: Full French interface with option to add more languages later.
```

---

## 📝 How to Use These Prompts in Cursor

1. **Copy the entire prompt** (including context)
2. **Paste into Cursor Chat** (Cmd+L or Ctrl+L)
3. **Cursor will**:
   - Read your existing code
   - Generate the required files
   - Show diffs for changes
   - Execute commands if needed
4. **Review and accept** the changes
5. **Move to next prompt**

---

## 🎯 Recommended Order

**Week 1**: Prompts 1-4 (REST API Foundation)  
**Week 2**: Prompts 5-7 (Business Logic & Signals)  
**Week 3**: Prompts 8-10 (Frontend - POS, Inventory, Reports)  
**Week 4**: Prompts 11-12 (PDF Receipts & Excel Exports)  
**Week 5**: Prompts 13-15 (Testing, Optimization & Production)  
**Week 6+**: Prompts 16-22 (Bonus Features as needed)

### Priority Order:
1. **Critical** (Must have for MVP):
   - Prompts 1-4: API foundation
   - Prompt 5: Stock auto-updates
   - Prompt 8: POS interface
   - Prompt 11: Receipt printing

2. **Important** (Needed for daily operations):
   - Prompt 6: Customer balance tracking
   - Prompt 9: Inventory management
   - Prompt 10: Reports dashboard
   - Prompt 12: Excel exports

3. **Enhancement** (For production quality):
   - Prompts 13-15: Testing & production
   - Prompt 21: Audit logging
   - Prompt 22: French localization

4. **Future** (Nice to have):
   - Prompts 16-20: Email, barcode, backup, multi-store, mobile

---

**Total: 22 prompts covering the complete application lifecycle!**

**Each prompt is self-contained and can be used independently in Cursor!**
