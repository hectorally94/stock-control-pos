"""
Excel Report Generator using openpyxl

All reports are scoped to an enterprise (multi-tenant safe) and deduplicated:
the inventory report aggregates one row per product, with the per-location
breakdown on its own sheet (a product stocked in N stores is NOT repeated N
times without context — that read as "duplicates" to users).
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from django.utils import timezone
from decimal import Decimal


# Rôle : formate un montant en texte sans décimales, avec espace pour les milliers et suffixe FB.
# Liens : utilisée seulement par sales_report dans ce fichier.
def format_currency(value):
    """Format as FB currency"""
    try:
        return f"{float(value):,.0f} FB".replace(',', ' ')
    except (TypeError, ValueError):
        return f"{value} FB"


# Rôle : applique le style d'en-tête (gras blanc, fond bleu, centré, bordures) à une ligne de feuille.
# Liens : appelée par les quatre rapports de ce fichier.
def apply_header_style(worksheet, row_num=1):
    """Apply header styling to a row"""
    for cell in worksheet[row_num]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )


# Rôle : met une ligne de total en gras sur fond gris, avec double bordure en haut.
# Liens : appelée par inventory_report et expense_report.
def apply_total_row_style(worksheet, row_num):
    """Apply total row styling"""
    for cell in worksheet[row_num]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E5E7EB", end_color="E5E7EB", fill_type="solid")
        cell.border = Border(top=Side(style='double'))


# Rôle : ajuste chaque colonne à son contenu le plus long, avec une largeur limitée à 50.
# Liens : appelée par les quatre rapports de ce fichier.
def auto_adjust_column_width(worksheet):
    """Auto-adjust column widths based on content"""
    for column in worksheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)

        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except (TypeError, ValueError):
                pass

        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width


# Rôle : écrit en haut de feuille le titre, le sous-titre éventuel et la date de génération.
# Liens : appelée par sales_report, inventory_report et expense_report.
def _report_header(ws, title, subtitle=''):
    """Standard report header: title, optional subtitle, generation stamp."""
    ws['A1'] = title
    ws['A1'].font = Font(size=16, bold=True, color="1E40AF")
    row = 2
    if subtitle:
        ws[f'A{row}'] = subtitle
        ws[f'A{row}'].font = Font(size=12)
        row += 1
    ws[f'A{row}'] = f"Généré le {timezone.localtime().strftime('%d/%m/%Y à %H:%M')}"
    ws[f'A{row}'].font = Font(size=9, italic=True, color="777777")


# Rôle : crée le classeur des ventes « completed » : résumé, ventes détaillées et articles vendus.
# Liens : appelée par export_sales_report (apps/reports/views.py) ; lit Sale et SaleItem.profit
# (apps/pos/models.py) ; filtres client, caissier, paiement et emplacement.
def sales_report(start_date, end_date, filters=None, enterprise=None):
    """
    Generate sales report Excel workbook (scoped to the enterprise).

    Args:
        start_date / end_date: report period
        filters: optional dict with customer_id, cashier_id, payment_method, location_id
        enterprise: scope every query to this enterprise
    """
    from apps.pos.models import Sale

    wb = Workbook()

    # Get sales (enterprise-scoped)
    sales = Sale.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        status='completed'
    ).select_related('customer', 'user', 'location')
    if enterprise:
        sales = sales.filter(enterprise=enterprise)

    location_name = None
    if filters:
        if filters.get('customer_id'):
            sales = sales.filter(customer_id=filters['customer_id'])
        if filters.get('cashier_id'):
            sales = sales.filter(user_id=filters['cashier_id'])
        if filters.get('payment_method'):
            sales = sales.filter(payment_method=filters['payment_method'])
        if filters.get('location_id'):
            sales = sales.filter(location_id=filters['location_id'])
            loc = sales.first()
            if loc and loc.location:
                location_name = loc.location.name
            else:
                from apps.locations.models import Location
                loc_obj = Location.objects.filter(pk=filters['location_id']).first()
                location_name = loc_obj.name if loc_obj else None

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Résumé"
    subtitle = f"Période: {start_date.strftime('%d/%m/%Y')} à {end_date.strftime('%d/%m/%Y')}"
    if location_name:
        subtitle += f" — Emplacement: {location_name}"
    _report_header(ws_summary, "RAPPORT DES VENTES", subtitle)

    # Summary stats
    total_sales = sales.count()
    total_amount = sum((sale.total_amount for sale in sales), Decimal('0'))
    avg_basket = total_amount / total_sales if total_sales > 0 else 0

    ws_summary['A5'] = "Nombre de ventes:"
    ws_summary['B5'] = total_sales
    ws_summary['A6'] = "Chiffre d'affaires:"
    ws_summary['B6'] = format_currency(total_amount)
    ws_summary['A7'] = "Panier moyen:"
    ws_summary['B7'] = format_currency(avg_basket)

    # Payment method breakdown
    ws_summary['A9'] = "Répartition par mode de paiement:"
    ws_summary['A9'].font = Font(bold=True)

    payment_methods = ['cash', 'mobile_money', 'card', 'credit']
    payment_labels = {
        'cash': 'Espèces',
        'mobile_money': 'Mobile Money',
        'card': 'Carte',
        'credit': 'Crédit'
    }

    row = 10
    for method in payment_methods:
        method_sales = sales.filter(payment_method=method)
        count = method_sales.count()
        amount = sum((sale.total_amount for sale in method_sales), Decimal('0'))

        ws_summary[f'A{row}'] = payment_labels[method]
        ws_summary[f'B{row}'] = count
        ws_summary[f'C{row}'] = format_currency(amount)
        row += 1

    # Sheet 2: Detailed Sales
    ws_sales = wb.create_sheet("Ventes Détaillées")

    headers = ['Date', 'N° Vente', 'Client', 'Caissier', 'Emplacement', 'Sous-total', 'Remise', 'TVA', 'Total', 'Paiement', 'Statut']
    ws_sales.append(headers)
    apply_header_style(ws_sales, 1)

    for sale in sales:
        ws_sales.append([
            sale.created_at.strftime('%d/%m/%Y %H:%M'),
            sale.sale_number,
            sale.customer.name if sale.customer else 'Anonyme',
            sale.user.get_full_name() or sale.user.username,
            sale.location.name if sale.location else '',
            float(sale.subtotal),
            float(sale.discount_amount),
            float(sale.tax_amount),
            float(sale.total_amount),
            sale.get_payment_method_display(),
            sale.get_status_display()
        ])

    # Format currency columns
    for row in range(2, ws_sales.max_row + 1):
        for col in [6, 7, 8, 9]:  # Subtotal, Discount, Tax, Total
            cell = ws_sales.cell(row, col)
            cell.number_format = '#,##0.00 "FB"'

    auto_adjust_column_width(ws_sales)
    ws_sales.freeze_panes = 'A2'

    # Sheet 3: Items Sold
    ws_items = wb.create_sheet("Articles Vendus")

    headers = ['Date', 'N° Vente', 'Produit', 'Catégorie', 'Qté', 'P.U.', 'P.A.', 'Total', 'Bénéfice']
    ws_items.append(headers)
    apply_header_style(ws_items, 1)

    for sale in sales.prefetch_related('items__product__category'):
        for item in sale.items.all():
            category = ''
            if item.product and item.product.category:
                category = item.product.category.name
            ws_items.append([
                sale.created_at.strftime('%d/%m/%Y'),
                sale.sale_number,
                item.product_name,
                category,
                float(item.quantity),
                float(item.unit_price),
                float(item.purchase_price),
                float(item.total_price),
                float(item.profit)
            ])

    # Format numbers
    for row in range(2, ws_items.max_row + 1):
        ws_items.cell(row, 5).number_format = '#,##0.00'  # Quantity
        for col in [6, 7, 8, 9]:  # Prices and profit
            ws_items.cell(row, col).number_format = '#,##0.00 "FB"'

    auto_adjust_column_width(ws_items)
    ws_items.freeze_panes = 'A2'

    return wb


# Rôle : crée le classeur d'inventaire : stock par produit, détail par emplacement, produits populaires.
# Liens : appelée par export_inventory_report (apps/reports/views.py) ; lit Stock (apps/stock/models.py)
# et Product (apps/products/models.py).
def inventory_report(enterprise=None, location=None):
    """
    Generate inventory report Excel workbook (scoped to the enterprise).

    Sheet 1 aggregates ONE row per product (no duplicates); the per-location
    breakdown lives on sheet 2 with an explicit "Emplacement" column.
    If `location` is given, the whole report is scoped to that location.
    """
    from django.db.models import Sum
    from apps.stock.models import Stock
    from apps.products.models import Product

    wb = Workbook()

    stocks = Stock.objects.select_related('product', 'product__category', 'location').order_by(
        'product__name', 'location__name'
    )
    if enterprise:
        stocks = stocks.filter(enterprise=enterprise)
    if location:
        stocks = stocks.filter(location=location)

    # Aggregate per product (dedup): total quantity across emplacements
    per_product = {}
    for stock in stocks:
        entry = per_product.setdefault(stock.product_id, {
            'product': stock.product,
            'quantity': Decimal('0'),
            'locations': 0,
        })
        entry['quantity'] += stock.quantity
        entry['locations'] += 1

    # Sheet 1: Stock by product (one row per product)
    ws = wb.active
    ws.title = "Stock par Produit"
    subtitle = f"Emplacement: {location.name}" if location else "Tous les emplacements"
    _report_header(ws, "RAPPORT D'INVENTAIRE", subtitle)
    ws.append([''])

    headers = ['Produit', 'Catégorie', 'Code-barres', 'Qté Totale', 'Seuil Min', 'Statut', 'Emplacements', 'Coût Unitaire', 'Valeur Totale']
    ws.append(headers)
    header_row = ws.max_row
    apply_header_style(ws, header_row)

    total_value = 0.0
    for entry in sorted(per_product.values(), key=lambda e: e['product'].name.lower()):
        product = entry['product']
        quantity = float(entry['quantity'])
        unit_cost = float(product.purchase_price)
        value = quantity * unit_cost
        total_value += value

        if quantity <= 0:
            status_text = "Rupture"
        elif quantity <= float(product.min_stock_threshold):
            status_text = "Stock faible"
        else:
            status_text = "En stock"

        ws.append([
            product.name,
            product.category.name if product.category else '',
            product.barcode or '',
            quantity,
            float(product.min_stock_threshold),
            status_text,
            entry['locations'],
            unit_cost,
            value
        ])

    # Add total row
    last_row = ws.max_row + 1
    ws[f'A{last_row}'] = "TOTAL"
    ws[f'I{last_row}'] = total_value
    apply_total_row_style(ws, last_row)

    for row in range(header_row + 1, ws.max_row + 1):
        ws.cell(row, 4).number_format = '#,##0.00'
        ws.cell(row, 8).number_format = '#,##0.00 "FB"'
        ws.cell(row, 9).number_format = '#,##0.00 "FB"'

    auto_adjust_column_width(ws)
    ws.freeze_panes = f'A{header_row + 1}'

    # Sheet 2: Detail by location (explicit Emplacement column)
    ws_detail = wb.create_sheet("Détail par Emplacement")
    headers = ['Produit', 'Catégorie', 'Emplacement', 'Quantité', 'Seuil Min', 'Statut']
    ws_detail.append(headers)
    apply_header_style(ws_detail, 1)

    for stock in stocks:
        product = stock.product
        if stock.quantity <= 0:
            status_text = "Rupture"
        elif stock.is_low_stock:
            status_text = "Stock faible"
        else:
            status_text = "En stock"
        ws_detail.append([
            product.name,
            product.category.name if product.category else '',
            stock.location.name if stock.location else 'Non assigné',
            float(stock.quantity),
            float(product.min_stock_threshold),
            status_text,
        ])

    for row in range(2, ws_detail.max_row + 1):
        ws_detail.cell(row, 4).number_format = '#,##0.00'

    auto_adjust_column_width(ws_detail)
    ws_detail.freeze_panes = 'A2'

    # Sheet 3: Popular Products
    ws_popular = wb.create_sheet("Produits Populaires")

    headers = ['Produit', 'Catégorie', 'Prix de Vente', 'Stock Actuel']
    ws_popular.append(headers)
    apply_header_style(ws_popular, 1)

    popular_products = Product.objects.filter(is_popular=True, is_active=True).select_related('category')
    if enterprise:
        popular_products = popular_products.filter(enterprise=enterprise)

    for product in popular_products:
        stock_qs = product.stock_info.all()
        if location:
            stock_qs = stock_qs.filter(location=location)
        stock_qty = float(stock_qs.aggregate(t=Sum('quantity'))['t'] or 0)

        ws_popular.append([
            product.name,
            product.category.name if product.category else '',
            float(product.sale_price),
            stock_qty
        ])

    for row in range(2, ws_popular.max_row + 1):
        ws_popular.cell(row, 3).number_format = '#,##0.00 "FB"'
        ws_popular.cell(row, 4).number_format = '#,##0.00'

    auto_adjust_column_width(ws_popular)
    ws_popular.freeze_panes = 'A2'

    return wb


# Rôle : crée le classeur des dépenses d'une période : synthèse par catégorie et liste détaillée.
# Liens : appelée par export_expense_report (apps/reports/views.py) ; lit Expense et ExpenseCategory
# (apps/accounting/models.py).
def expense_report(start_date, end_date, enterprise=None):
    """Generate expense report Excel workbook (scoped to the enterprise)."""
    from apps.accounting.models import Expense, ExpenseCategory
    from django.db.models import Q

    wb = Workbook()

    # Sheet 1: Summary by Category
    ws_summary = wb.active
    ws_summary.title = "Dépenses par Catégorie"
    _report_header(
        ws_summary, "RAPPORT DES DÉPENSES",
        f"Période: {start_date.strftime('%d/%m/%Y')} à {end_date.strftime('%d/%m/%Y')}"
    )

    expenses = Expense.objects.filter(
        expense_date__gte=start_date,
        expense_date__lte=end_date
    ).select_related('expense_category', 'user', 'location')
    if enterprise:
        expenses = expenses.filter(enterprise=enterprise)

    total_amount = sum((exp.amount for exp in expenses), Decimal('0'))

    headers = ['Catégorie', 'Montant', 'Nombre', 'Montant Moyen', '% du Total']
    ws_summary.append([''])
    ws_summary.append(headers)
    header_row = ws_summary.max_row
    apply_header_style(ws_summary, header_row)

    categories = ExpenseCategory.objects.all()
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Rôle : ajoute la ligne d'une catégorie (montant, nombre, moyenne, part du total) si elle a des dépenses.
    # Liens : fonction locale, appelée seulement par expense_report.
    def _append_summary_row(label, cat_expenses):
        count = cat_expenses.count()
        if count == 0:
            return
        amount = sum((exp.amount for exp in cat_expenses), Decimal('0'))
        avg = amount / count
        # Fraction (0-1): the Excel % format multiplies by 100 itself
        fraction = float(amount / total_amount) if total_amount > 0 else 0
        ws_summary.append([label, float(amount), count, float(avg), fraction])

    for category in categories:
        _append_summary_row(category.name, expenses.filter(expense_category=category))
    _append_summary_row('Sans catégorie', expenses.filter(expense_category__isnull=True))

    # Add total row
    last_row = ws_summary.max_row + 1
    ws_summary[f'A{last_row}'] = "TOTAL"
    ws_summary[f'B{last_row}'] = float(total_amount)
    ws_summary[f'C{last_row}'] = expenses.count()
    apply_total_row_style(ws_summary, last_row)

    for row in range(header_row + 1, ws_summary.max_row + 1):
        ws_summary.cell(row, 2).number_format = '#,##0.00 "FB"'
        ws_summary.cell(row, 4).number_format = '#,##0.00 "FB"'
        ws_summary.cell(row, 5).number_format = '0.00%'

    auto_adjust_column_width(ws_summary)

    # Sheet 2: Detailed Expenses
    ws_details = wb.create_sheet("Dépenses Détaillées")

    headers = ['Date', 'Catégorie', 'Description', 'Montant', 'Paiement', 'Fournisseur', 'Référence', 'Emplacement', 'Utilisateur']
    ws_details.append(headers)
    apply_header_style(ws_details, 1)

    for expense in expenses:
        ws_details.append([
            expense.expense_date.strftime('%d/%m/%Y'),
            expense.expense_category.name if expense.expense_category else 'Sans catégorie',
            expense.description,
            float(expense.amount),
            expense.get_payment_method_display(),
            expense.supplier or '',
            expense.reference or '',
            expense.location.name if expense.location else '',
            expense.user.get_full_name() or expense.user.username
        ])

    for row in range(2, ws_details.max_row + 1):
        ws_details.cell(row, 4).number_format = '#,##0.00 "FB"'

    auto_adjust_column_width(ws_details)
    ws_details.freeze_panes = 'A2'

    return wb


# Rôle : crée le classeur clients : 100 meilleurs clients et clients ayant un solde de crédit.
# Liens : appelée par export_customer_report (apps/reports/views.py) ; lit Customer (apps/customers/models.py).
def customer_report(enterprise=None):
    """Generate customer report Excel workbook (scoped to the enterprise)."""
    from django.db.models import Q
    from apps.customers.models import Customer

    wb = Workbook()

    customers_qs = Customer.objects.filter(is_active=True)
    if enterprise:
        customers_qs = customers_qs.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Sheet 1: Top Customers
    ws = wb.active
    ws.title = "Top Clients"

    headers = ['Rang', 'Client', 'Téléphone', 'Total Achats', 'Nb Achats', 'Panier Moyen', 'Solde Crédit', 'Points Fidélité']
    ws.append(headers)
    apply_header_style(ws, 1)

    customers = customers_qs.order_by('-total_purchases')[:100]

    for rank, customer in enumerate(customers, 1):
        avg_basket = customer.total_purchases / customer.purchase_count if customer.purchase_count > 0 else 0

        ws.append([
            rank,
            customer.name,
            customer.phone or '',
            float(customer.total_purchases),
            customer.purchase_count,
            float(avg_basket),
            float(customer.current_balance),
            customer.loyalty_points
        ])

    for row in range(2, ws.max_row + 1):
        for col in [4, 6, 7]:
            ws.cell(row, col).number_format = '#,##0.00 "FB"'

    auto_adjust_column_width(ws)
    ws.freeze_panes = 'A2'

    # Sheet 2: Customers with Credit
    ws_credit = wb.create_sheet("Clients avec Crédit")

    headers = ['Client', 'Téléphone', 'Solde Dû', 'Limite Crédit', '% Utilisé']
    ws_credit.append(headers)
    apply_header_style(ws_credit, 1)

    credit_customers = customers_qs.filter(current_balance__gt=0).order_by('-current_balance')

    for customer in credit_customers:
        # Fraction (0-1): the Excel % format multiplies by 100 itself
        utilization = float(customer.current_balance / customer.credit_limit) if customer.credit_limit > 0 else 0

        ws_credit.append([
            customer.name,
            customer.phone or '',
            float(customer.current_balance),
            float(customer.credit_limit),
            utilization
        ])

    for row in range(2, ws_credit.max_row + 1):
        ws_credit.cell(row, 3).number_format = '#,##0.00 "FB"'
        ws_credit.cell(row, 4).number_format = '#,##0.00 "FB"'
        ws_credit.cell(row, 5).number_format = '0.00%'

    auto_adjust_column_width(ws_credit)
    ws_credit.freeze_panes = 'A2'

    return wb
