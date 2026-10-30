"""
Frontend views for Stock Management
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import timedelta
import json

from apps.stock.models import Stock, StockMovement
from apps.products.models import Product, Category
from apps.locations.models import Location, LocationStock
from apps.core.exports import export_list_response, fmt_qty

# French labels for StockMovement.reason (plain CharField, no choices)
REASON_LABELS = {
    'purchase': 'Achat',
    'sale': 'Vente POS',
    'manual_sale': 'Vente Manuelle',
    'customer_return': 'Retour Client',
    'loss': 'Perte',
    'breakage': 'Casse',
    'expiration': 'Expiration',
    'correction': 'Correction',
    'initial_stock': 'Stock Initial',
    'transfer_in': 'Transfert Entrant',
    'transfer_out': 'Transfert Sortant',
    'other_entry': 'Autre Entrée',
    'other_exit': 'Autre Sortie',
}


# Rôle : calcule les compteurs, listes d'alertes et données JSON des graphiques (14 jours, mois en cours).
# Liens : route /stock/ ; lit Stock, StockMovement, Location, LocationStock ; lien depuis templates/base.html ;
# rend apps/stock/templates/stock/dashboard.html, dont les graphiques Chart.js utilisent ces données.
@login_required
def dashboard_view(request):
    """Stock dashboard with charts and analytics"""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    today = timezone.now().date()

    # Base querysets filtered by enterprise
    stock_qs = Stock.objects.select_related('product', 'location')
    movement_qs = StockMovement.objects.select_related('product', 'user', 'location')

    if enterprise:
        stock_qs = stock_qs.filter(enterprise=enterprise)
        movement_qs = movement_qs.filter(enterprise=enterprise)

    # --- SUMMARY STATS ---

    # Total products actually in stock (quantity > 0) — matches the "Produits
    # en Stock" detail page (stock:in_stock). Products with only zero rows are
    # counted under "Rupture de Stock" instead.
    total_products = stock_qs.filter(quantity__gt=0).values('product').distinct().count()

    # Total stock quantity (units)
    total_quantity = stock_qs.aggregate(total=Sum('quantity'))['total'] or 0

    # Get low stock items (below threshold but still > 0) and out-of-stock (= 0)
    low_stock_items = []
    out_of_stock_items = []
    for stock in stock_qs.all():
        if stock.quantity <= 0:
            out_of_stock_items.append(stock)
        elif stock.is_low_stock:
            low_stock_items.append(stock)

    # Out of stock count
    out_of_stock = len(out_of_stock_items)

    # Movements today
    movements_today = movement_qs.filter(created_at__date=today).count()

    # Recent movements (last 20)
    recent_movements = movement_qs.order_by('-created_at')[:20]

    # --- CHART DATA ---

    # 1. Stock movements by day (last 14 days)
    movement_labels = []
    movement_dates = []  # ISO dates so chart bars can link to that day's movements
    entry_data = []
    exit_data = []

    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        movement_labels.append(day.strftime('%d/%m'))
        movement_dates.append(day.isoformat())

        day_movements = movement_qs.filter(created_at__date=day)

        entries = day_movements.filter(movement_type='entry').aggregate(
            total=Sum('quantity')
        )['total'] or 0
        exits = day_movements.filter(movement_type='exit').aggregate(
            total=Sum('quantity')
        )['total'] or 0

        entry_data.append(float(entries))
        exit_data.append(float(exits))

    # 2. Stock by category
    category_stock = stock_qs.values(
        'product__category__id', 'product__category__name'
    ).annotate(
        total_qty=Sum('quantity'),
        product_count=Count('product', distinct=True)
    ).order_by('-total_qty')[:6]

    category_labels = [c['product__category__name'] or 'Sans catégorie' for c in category_stock]
    category_data = [float(c['total_qty'] or 0) for c in category_stock]
    category_ids = [c['product__category__id'] for c in category_stock]

    # 3. Movement reasons distribution (this month)
    month_start = today.replace(day=1)
    reason_stats = movement_qs.filter(
        created_at__date__gte=month_start
    ).values('reason').annotate(
        count=Count('id')
    ).order_by('-count')[:8]

    reason_names = {
        'purchase': 'Achat',
        'sale': 'Vente POS',
        'manual_sale': 'Vente Manuelle',
        'customer_return': 'Retour Client',
        'loss': 'Perte',
        'breakage': 'Casse',
        'expiration': 'Expiration',
        'correction': 'Correction',
        'initial_stock': 'Stock Initial',
        'transfer_in': 'Transfert Entrant',
        'transfer_out': 'Transfert Sortant',
        'other_entry': 'Autre Entrée',
        'other_exit': 'Autre Sortie',
    }

    reason_labels = [reason_names.get(r['reason'], r['reason']) for r in reason_stats]
    reason_data = [r['count'] for r in reason_stats]
    reason_codes = [r['reason'] for r in reason_stats]

    # 4. Stock levels by location
    location_stock = []
    if enterprise:
        locations = Location.objects.filter(enterprise=enterprise, is_active=True)
        for loc in locations:
            loc_stock = LocationStock.objects.filter(location=loc).aggregate(
                total=Sum('quantity'),
                products=Count('product', distinct=True),
                low=Count('id', filter=Q(quantity__lte=F('min_stock_threshold')))
            )
            location_stock.append({
                'id': loc.id,
                'name': loc.name,
                'type': loc.location_type,
                'total': float(loc_stock['total'] or 0),
                'products': loc_stock['products'] or 0,
                'low': loc_stock['low'] or 0
            })

    # 5. Top products by stock quantity
    top_stock_products = stock_qs.values(
        'product__id', 'product__name'
    ).annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty')[:10]

    top_product_labels = [p['product__name'][:20] for p in top_stock_products]
    top_product_data = [float(p['total_qty'] or 0) for p in top_stock_products]
    top_product_ids = [p['product__id'] for p in top_stock_products]

    # 6. Entry vs Exit totals (this month)
    month_entries = movement_qs.filter(
        created_at__date__gte=month_start,
        movement_type='entry'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    month_exits = movement_qs.filter(
        created_at__date__gte=month_start,
        movement_type='exit'
    ).aggregate(total=Sum('quantity'))['total'] or 0

    context = {
        # Summary stats
        'total_products': total_products,
        'total_quantity': total_quantity,
        'low_stock_count': len(low_stock_items),
        'out_of_stock': out_of_stock,
        'movements_today': movements_today,
        'month_entries': month_entries,
        'month_exits': month_exits,
        # Tables
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'recent_movements': recent_movements,
        'location_stock': location_stock,
        # Chart data (JSON)
        'movement_labels': json.dumps(movement_labels),
        'movement_dates': json.dumps(movement_dates),
        'entry_data': json.dumps(entry_data),
        'exit_data': json.dumps(exit_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'category_ids': json.dumps(category_ids),
        'reason_labels': json.dumps(reason_labels),
        'reason_data': json.dumps(reason_data),
        'reason_codes': json.dumps(reason_codes),
        'top_product_labels': json.dumps(top_product_labels),
        'top_product_data': json.dumps(top_product_data),
        'top_product_ids': json.dumps(top_product_ids),
    }

    return render(request, 'stock/dashboard.html', context)


# Rôle : affiche et traite le formulaire d'entrée de stock ; accepte ?product=, ?location= et ?next=.
# Liens : route /stock/entry/ ; crée un StockMovement, dont save() met à jour le stock ;
# rend apps/stock/templates/stock/entry.html (products_json alimente stockEntryForm).
@login_required
def entry_view(request):
    """Stock entry form"""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = getattr(user, 'location', None)

    # Where to return after saving (e.g. back to the location we came from)
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    safe_next = next_url if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ) else ''

    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation

        product_id = (request.POST.get('product') or '').strip()
        quantity_str = (request.POST.get('quantity') or '').strip()
        unit_cost_str = (request.POST.get('unit_cost') or '').strip()
        reason = request.POST.get('reason', 'purchase')
        reference = request.POST.get('reference', '')
        notes = request.POST.get('notes', '')
        location_id = (request.POST.get('location') or '').strip()

        errors = []

        # --- Produit (obligatoire, scopé à l'entreprise de l'utilisateur) ---
        product = None
        if not product_id:
            errors.append("Veuillez sélectionner un produit dans la liste.")
        elif not product_id.isdigit():
            errors.append("Produit invalide.")
        else:
            product_qs = Product.objects.filter(id=product_id, is_active=True)
            if enterprise:
                product_qs = product_qs.filter(enterprise=enterprise)
            product = product_qs.first()
            if product is None:
                errors.append("Produit introuvable ou inactif.")

        # --- Quantité (obligatoire, > 0) ---
        quantity = None
        try:
            quantity = Decimal(quantity_str)
        except (InvalidOperation, ValueError, TypeError):
            errors.append("Quantité invalide.")
        else:
            if quantity <= 0:
                errors.append("La quantité doit être supérieure à zéro.")

        # --- Coût unitaire (optionnel, >= 0) ---
        unit_cost = None
        if unit_cost_str:
            try:
                unit_cost = Decimal(unit_cost_str)
            except (InvalidOperation, ValueError, TypeError):
                errors.append("Coût unitaire invalide.")
            else:
                if unit_cost < 0:
                    errors.append("Le coût unitaire ne peut pas être négatif.")

        # --- Emplacement (optionnel, défaut = emplacement de l'utilisateur) ---
        entry_location = None
        if location_id:
            if not location_id.isdigit():
                errors.append("Emplacement invalide.")
            else:
                location_qs = Location.objects.filter(id=location_id, is_active=True)
                if enterprise:
                    location_qs = location_qs.filter(enterprise=enterprise)
                entry_location = location_qs.first()
                if entry_location is None:
                    errors.append("Emplacement introuvable.")
        elif location:
            entry_location = location

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            try:
                StockMovement.objects.create(
                    product=product,
                    user=request.user,
                    enterprise=enterprise,
                    location=entry_location,
                    movement_type='entry',
                    reason=reason,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    reference=reference,
                    notes=notes
                )
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement: {e}")
            else:
                messages.success(request, f"Entrée de stock enregistrée pour {product.name}")
                return redirect(safe_next or 'stock:dashboard')

    products = Product.objects.filter(is_active=True).select_related('category')
    if enterprise:
        products = products.filter(enterprise=enterprise)
    products = products.order_by('name')

    # Compact JSON list powering the searchable product combobox (Alpine.js).
    # `price` (sale price) lets the form auto-fill the unit cost on selection.
    products_json = [
        {
            'id': p.id,
            'label': f"{p.name} ({p.category.name})" if p.category else p.name,
            'price': float(p.sale_price or 0),
        }
        for p in products
    ]

    # Product can be pre-selected via ?product=<pk> (e.g. "Entrée stock" button
    # on the product detail page) — preselects the combobox and fills the cost.
    preselected_product_id = request.GET.get('product', '')

    locations = []
    if enterprise:
        locations = Location.objects.filter(enterprise=enterprise, is_active=True)

    # Emplacement can be locked via ?location=<pk> (e.g. "Entrée" button from a
    # location page) — the form then targets that location, no dropdown shown.
    preselected_location = None
    preselected_location_id = request.GET.get('location', '')
    if preselected_location_id and enterprise:
        preselected_location = Location.objects.filter(
            id=preselected_location_id, enterprise=enterprise, is_active=True
        ).first()

    # Can this user create a product? (drives the empty-state CTA)
    can_create_product = request.user.role in ['admin', 'owner', 'manager']

    context = {
        'products': products,
        'products_json': products_json,
        'preselected_product_id': preselected_product_id,
        'has_products': bool(products_json),
        'can_create_product': can_create_product,
        'locations': locations,
        'user_location': location,
        'preselected_location': preselected_location,
        'next_url': safe_next,
    }

    return render(request, 'stock/entry.html', context)


# Rôle : liste le stock positif en deux onglets (par produit, par produit et emplacement), filtres et export.
# Liens : route /stock/in-stock/ ; lit Stock ; export via export_list_response (apps/core/exports.py) ;
# rend apps/stock/templates/stock/in_stock.html ; atteinte depuis apps/stock/templates/stock/dashboard.html.
@login_required
def in_stock_view(request):
    """Products in stock — two views: by product (the distinct count) and by
    unit detail (every product x emplacement row that makes up the total units).
    Reached from the "Produits en Stock" dashboard card."""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    stock_qs = Stock.objects.select_related('product', 'product__category', 'location')
    if enterprise:
        stock_qs = stock_qs.filter(enterprise=enterprise)

    # Only rows that actually hold stock
    in_stock = stock_qs.filter(quantity__gt=0)

    # Filter dropdown data
    locations = Location.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.filter(is_active=True).order_by('name')
    if enterprise:
        locations = locations.filter(enterprise=enterprise)
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Filters (apply to both tabs)
    search = request.GET.get('search', '').strip()
    if search:
        in_stock = in_stock.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(product__barcode__icontains=search)
        )
    location_filter = request.GET.get('location')
    if location_filter:
        in_stock = in_stock.filter(location_id=location_filter)
    category_filter = request.GET.get('category')
    if category_filter:
        in_stock = in_stock.filter(product__category_id=category_filter)

    # --- "Détail des unités" tab: one row per product x emplacement ---
    stock_rows = in_stock.order_by('product__name', 'location__name')

    # --- "Par produit" tab: distinct products with their total quantity ---
    agg = in_stock.values('product').annotate(
        total_qty=Sum('quantity'),
        loc_count=Count('location', distinct=True),
    )
    prod_map = {
        p.id: p
        for p in Product.objects.filter(id__in=[a['product'] for a in agg]).select_related('category')
    }
    by_product = [
        {'product': prod_map[a['product']], 'total_qty': a['total_qty'], 'loc_count': a['loc_count']}
        for a in agg if a['product'] in prod_map
    ]
    by_product.sort(key=lambda x: x['product'].name.lower())

    total_products = len(by_product)
    total_quantity = sum((x['total_qty'] for x in by_product), 0)

    # Export the active tab's data
    if request.GET.get('tab') == 'units':
        export = export_list_response(
            request,
            title="Produits en Stock — Détail des unités",
            headers=["Produit", "Catégorie", "Emplacement", "Quantité", "Unité"],
            rows=(
                [
                    s.product.name,
                    s.product.category.name if s.product.category else '',
                    s.location.name if s.location else '',
                    fmt_qty(s.quantity),
                    s.product.unit,
                ]
                for s in stock_rows
            ),
            filename="stock_detail_unites",
        )
    else:
        export = export_list_response(
            request,
            title="Produits en Stock",
            headers=["Produit", "Catégorie", "Quantité totale", "Unité", "Emplacements"],
            rows=(
                [
                    x['product'].name,
                    x['product'].category.name if x['product'].category else '',
                    fmt_qty(x['total_qty']),
                    x['product'].unit,
                    x['loc_count'],
                ]
                for x in by_product
            ),
            filename="produits_en_stock",
        )
    if export:
        return export

    context = {
        'stock_rows': stock_rows,
        'by_product': by_product,
        'total_products': total_products,
        'total_quantity': total_quantity,
        'locations': locations,
        'categories': categories,
        'search': search,
        'selected_location': location_filter,
        'selected_category': category_filter,
        'active_tab': 'units' if request.GET.get('tab') == 'units' else 'products',
    }
    return render(request, 'stock/in_stock.html', context)


# Rôle : prépare l'export PDF/Excel commun aux listes de stock ; retourne None si ?export= est absent.
# Liens : appelée par low_stock_view et out_of_stock_view ; utilise export_list_response (apps/core/exports.py).
def _stock_list_export(request, title, filename, items):
    """Shared export for the Stock Faible / Rupture de Stock lists."""
    return export_list_response(
        request,
        title=title,
        headers=["Produit", "Catégorie", "Emplacement", "Stock actuel", "Seuil min", "Unité"],
        rows=(
            [
                s.product.name,
                s.product.category.name if s.product.category else '',
                s.location.name if s.location else '',
                fmt_qty(s.quantity),
                fmt_qty(s.product.min_stock_threshold),
                s.product.unit,
            ]
            for s in items
        ),
        filename=filename,
    )


# Rôle : liste les lignes Stock sous le seuil du produit mais encore positives ; le filtre se fait en Python.
# Liens : route /stock/low-stock/ ; lit Stock.is_low_stock ; lien de apps/core/dashboard_views.py ;
# rend apps/stock/templates/stock/stock_list.html.
@login_required
def low_stock_view(request):
    """List products with low stock"""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    stock_qs = Stock.objects.select_related('product', 'product__category', 'location')
    if enterprise:
        stock_qs = stock_qs.filter(enterprise=enterprise)

    # Get low stock items
    low_stock_items = []
    for stock in stock_qs.all():
        if stock.is_low_stock and stock.quantity > 0:
            low_stock_items.append(stock)

    export = _stock_list_export(request, "Stock Faible", "stock_faible", low_stock_items)
    if export:
        return export

    context = {
        'low_stock_items': low_stock_items,
        'title': 'Stock Faible',
        'icon': 'exclamation-triangle',
        'color': 'yellow',
    }
    return render(request, 'stock/stock_list.html', context)


# Rôle : liste les lignes Stock à quantité nulle ou négative, avec le même template que le stock faible.
# Liens : route /stock/out-of-stock/ ; utilise _stock_list_export ; lien depuis apps/core/dashboard_views.py ;
# rend apps/stock/templates/stock/stock_list.html.
@login_required
def out_of_stock_view(request):
    """List products that are out of stock"""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    stock_qs = Stock.objects.select_related('product', 'product__category', 'location')
    if enterprise:
        stock_qs = stock_qs.filter(enterprise=enterprise)

    out_of_stock_items = stock_qs.filter(quantity__lte=0)

    export = _stock_list_export(request, "Rupture de Stock", "rupture_de_stock", out_of_stock_items)
    if export:
        return export

    context = {
        'low_stock_items': out_of_stock_items,
        'title': 'Rupture de Stock',
        'icon': 'times-circle',
        'color': 'red',
    }
    return render(request, 'stock/stock_list.html', context)


# Rôle : historique paginé (50 par page) ; filtres type, raison, date, recherche, produit, emplacement ; export.
# Liens : route /stock/movements/ ; lit StockMovement ; export via export_list_response (apps/core/exports.py) ;
# rend apps/stock/templates/stock/movements.html ; atteinte depuis les graphiques du tableau de bord du stock.
@login_required
def movements_view(request):
    """List all stock movements with filters"""
    if request.user.role not in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    today = timezone.now().date()

    movements = StockMovement.objects.select_related('product', 'user', 'location').order_by('-created_at')
    if enterprise:
        movements = movements.filter(enterprise=enterprise)

    # Filters
    movement_type = request.GET.get('type')
    if movement_type in ['entry', 'exit']:
        movements = movements.filter(movement_type=movement_type)

    reason = request.GET.get('reason')
    if reason:
        movements = movements.filter(reason=reason)

    date_filter = request.GET.get('date')
    filter_day = None
    if date_filter == 'today':
        movements = movements.filter(created_at__date=today)
    elif date_filter == 'week':
        week_start = today - timedelta(days=today.weekday())
        movements = movements.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        month_start = today.replace(day=1)
        movements = movements.filter(created_at__date__gte=month_start)
    elif date_filter:
        # Exact day (YYYY-MM-DD) — used by the dashboard chart bars
        from datetime import datetime
        try:
            filter_day = datetime.strptime(date_filter, '%Y-%m-%d').date()
            movements = movements.filter(created_at__date=filter_day)
        except ValueError:
            date_filter = None

    search = request.GET.get('search', '').strip()
    if search:
        movements = movements.filter(
            Q(product__name__icontains=search) |
            Q(reference__icontains=search) |
            Q(notes__icontains=search)
        )

    # Scope to a single product / location (e.g. "Historique" from a location page)
    filter_product = None
    product_id = request.GET.get('product')
    if product_id:
        movements = movements.filter(product_id=product_id)
        filter_product = Product.objects.filter(id=product_id).first()

    filter_location = None
    location_id = request.GET.get('location')
    if location_id:
        movements = movements.filter(location_id=location_id)
        filter_location = Location.objects.filter(id=location_id).first()

    # Export (respects the active filters, before pagination)
    export = export_list_response(
        request,
        title="Mouvements de Stock",
        headers=["Date", "Produit", "Type", "Quantité", "Raison", "Référence", "Emplacement", "Par"],
        rows=(
            [
                m.created_at,
                m.product.name,
                'Entrée' if m.movement_type == 'entry' else 'Sortie',
                ('+' if m.movement_type == 'entry' else '-') + fmt_qty(m.quantity),
                REASON_LABELS.get(m.reason, m.reason),
                m.reference or '',
                m.location.name if m.location else '',
                m.user.get_full_name() or m.user.username if m.user else '',
            ]
            for m in movements
        ),
        filename="mouvements_stock",
    )
    if export:
        return export

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(movements, 50)
    page = request.GET.get('page', 1)
    movements = paginator.get_page(page)

    # Reason choices for filter
    reason_choices = [
        ('purchase', 'Achat'),
        ('sale', 'Vente POS'),
        ('manual_sale', 'Vente Manuelle'),
        ('customer_return', 'Retour Client'),
        ('loss', 'Perte'),
        ('breakage', 'Casse'),
        ('expiration', 'Expiration'),
        ('correction', 'Correction'),
        ('initial_stock', 'Stock Initial'),
        ('transfer_in', 'Transfert Entrant'),
        ('transfer_out', 'Transfert Sortant'),
    ]

    context = {
        'movements': movements,
        'reason_choices': reason_choices,
        'selected_type': movement_type,
        'selected_reason': reason,
        'selected_date': date_filter,
        'search': search,
        'filter_product': filter_product,
        'filter_location': filter_location,
        'filter_day': filter_day,
    }
    return render(request, 'stock/movements.html', context)
