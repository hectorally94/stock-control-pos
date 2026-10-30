"""
Frontend views for POS interface
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from apps.pos.models import Sale, SaleItem
from apps.products.models import Product, Category
from apps.customers.models import Customer
from apps.stock.models import Stock
from apps.pos.utils.receipt_generator import generate_receipt_pdf
from apps.core.exports import export_list_response

PAYMENT_METHOD_LABELS = {
    'cash': 'Espèces',
    'mobile_money': 'Mobile Money',
    'card': 'Carte',
    'credit': 'Crédit',
    'other': 'Autre',
}

SALE_STATUS_LABELS = {
    'completed': 'Complétée',
    'refunded': 'Remboursée',
    'cancelled': 'Annulée',
}


@login_required
def sales_list(request):
    """Sales history with filters — drill-down target for the dashboards."""
    if request.user.role not in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = getattr(user, 'location', None)
    today = timezone.now().date()

    sales = Sale.objects.select_related('customer', 'user', 'location').order_by('-created_at')
    if enterprise:
        sales = sales.filter(enterprise=enterprise)
    # Cashiers / boutique managers only see their own location (same as the dashboard)
    if location and user.role in ['cashier', 'boutique_manager']:
        sales = sales.filter(location=location)

    # Status filter (default: completed — what the dashboard numbers count)
    status = request.GET.get('status', 'completed')
    if status in dict(Sale.STATUS_CHOICES):
        sales = sales.filter(status=status)
    else:
        status = ''

    # Date filters: today | week | month | exact day (YYYY-MM-DD) | start/end range
    date_filter = request.GET.get('date', '')
    filter_day = None
    if date_filter == 'today':
        sales = sales.filter(created_at__date=today)
    elif date_filter == 'week':
        week_start = today - timedelta(days=today.weekday())
        sales = sales.filter(created_at__date__gte=week_start)
    elif date_filter == 'month':
        sales = sales.filter(created_at__date__gte=today.replace(day=1))
    elif date_filter:
        from datetime import datetime
        try:
            filter_day = datetime.strptime(date_filter, '%Y-%m-%d').date()
            sales = sales.filter(created_at__date=filter_day)
        except ValueError:
            date_filter = ''

    start = request.GET.get('start')
    end = request.GET.get('end')
    if start and end:
        from datetime import datetime
        try:
            start_d = datetime.strptime(start, '%Y-%m-%d').date()
            end_d = datetime.strptime(end, '%Y-%m-%d').date()
            sales = sales.filter(created_at__date__gte=start_d, created_at__date__lte=end_d)
        except ValueError:
            start = end = None

    # Payment method
    payment = request.GET.get('payment', '')
    if payment in dict(Sale.PAYMENT_METHOD_CHOICES):
        sales = sales.filter(payment_method=payment)
    else:
        payment = ''

    # Category (via sale items)
    filter_category = None
    category_id = request.GET.get('category')
    if category_id:
        sales = sales.filter(items__product__category_id=category_id).distinct()
        filter_category = Category.objects.filter(id=category_id).first()

    # Location (managers only — cashiers are already locked to their own)
    filter_location = None
    loc_id = request.GET.get('location')
    if loc_id and not (location and user.role in ['cashier', 'boutique_manager']):
        from apps.locations.models import Location
        filter_location = Location.objects.filter(id=loc_id, enterprise=enterprise).first()
        if filter_location:
            sales = sales.filter(location=filter_location)

    # Cashier
    filter_cashier = None
    cashier_id = request.GET.get('cashier')
    if cashier_id:
        sales = sales.filter(user_id=cashier_id)
        from apps.accounts.models import User
        filter_cashier = User.objects.filter(id=cashier_id).first()

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        sales = sales.filter(
            Q(sale_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(payment_reference__icontains=search)
        )

    # Totals of the filtered set
    totals = sales.aggregate(total=Sum('total_amount'), count=Count('id'))

    # Export (respects the active filters)
    export = export_list_response(
        request,
        title="Historique des Ventes",
        headers=["N° Vente", "Date", "Client", "Caissier", "Emplacement", "Paiement", "Statut", "Total (FB)"],
        rows=(
            [
                s.sale_number,
                s.created_at,
                s.customer.name if s.customer else 'Client comptant',
                s.user.get_full_name() or s.user.username if s.user else '',
                s.location.name if s.location else '',
                PAYMENT_METHOD_LABELS.get(s.payment_method, s.payment_method),
                SALE_STATUS_LABELS.get(s.status, s.status),
                float(s.total_amount or 0),
            ]
            for s in sales
        ),
        filename="ventes",
    )
    if export:
        return export

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(sales, 50)
    sales_page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'sales': sales_page,
        'totals': totals,
        'selected_status': status,
        'selected_date': date_filter,
        'selected_payment': payment,
        'filter_day': filter_day,
        'filter_category': filter_category,
        'filter_cashier': filter_cashier,
        'filter_location': filter_location,
        'search': search,
        'start': start or '',
        'end': end or '',
        'payment_choices': [(k, PAYMENT_METHOD_LABELS.get(k, v)) for k, v in Sale.PAYMENT_METHOD_CHOICES],
        'status_choices': [(k, SALE_STATUS_LABELS.get(k, v)) for k, v in Sale.STATUS_CHOICES],
    }
    return render(request, 'pos/sales_list.html', context)


@login_required
def sales_dashboard(request):
    """
    POS Sales Dashboard with charts and statistics
    """
    if request.user.role not in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = getattr(user, 'location', None)
    today = timezone.now().date()

    # Base queryset
    sales_qs = Sale.objects.select_related('customer', 'user')
    if enterprise:
        sales_qs = sales_qs.filter(enterprise=enterprise)
    if location and user.role in ['cashier', 'boutique_manager']:
        sales_qs = sales_qs.filter(location=location)

    # --- TODAY'S STATS ---
    today_sales = sales_qs.filter(created_at__date=today, status='completed')
    today_stats = today_sales.aggregate(
        total=Sum('total_amount'),
        count=Count('id'),
        avg=Avg('total_amount')
    )

    # --- THIS WEEK ---
    week_start = today - timedelta(days=today.weekday())
    week_sales = sales_qs.filter(
        created_at__date__gte=week_start,
        status='completed'
    )
    week_stats = week_sales.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    # --- THIS MONTH ---
    month_start = today.replace(day=1)
    month_sales = sales_qs.filter(
        created_at__date__gte=month_start,
        status='completed'
    )
    month_stats = month_sales.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    # --- CREDIT TRACKING (vendu vs encaissé vs crédit) ---
    from apps.customers.models import CustomerCredit, CreditPayment
    credits_qs = CustomerCredit.objects.all()
    payments_qs = CreditPayment.objects.all()
    if enterprise:
        credits_qs = credits_qs.filter(customer__enterprise=enterprise)
        payments_qs = payments_qs.filter(credit__customer__enterprise=enterprise)
    if location and user.role in ['cashier', 'boutique_manager']:
        credits_qs = credits_qs.filter(sale__location=location)
        payments_qs = payments_qs.filter(credit__sale__location=location)

    today_credit_given = credits_qs.filter(created_at__date=today).aggregate(
        t=Sum('original_amount'))['t'] or Decimal('0')
    today_repayments = payments_qs.filter(created_at__date=today).aggregate(
        t=Sum('amount'))['t'] or Decimal('0')
    # Encaissé = ventes du jour moins la part vendue à crédit, plus les remboursements reçus
    today_collected = (today_stats['total'] or Decimal('0')) - today_credit_given + today_repayments

    open_credits = credits_qs.filter(status__in=['pending', 'partial'])
    credit_outstanding = open_credits.aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
    credit_debtors = open_credits.values('customer').distinct().count()

    # --- CHART DATA ---

    # 1. Sales trend (last 7 days)
    trend_labels = []
    trend_dates = []  # ISO dates for chart drill-down links
    trend_data = []
    trend_count = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        trend_labels.append(day.strftime('%d/%m'))
        trend_dates.append(day.isoformat())

        day_sales = sales_qs.filter(created_at__date=day, status='completed')
        stats = day_sales.aggregate(total=Sum('total_amount'), count=Count('id'))
        trend_data.append(float(stats['total'] or 0))
        trend_count.append(stats['count'] or 0)

    # 2. Sales by payment method (today)
    payment_stats = today_sales.values('payment_method').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')

    payment_method_names = {
        'cash': 'Espèces',
        'card': 'Carte',
        'mobile_money': 'Mobile Money',
        'credit': 'Crédit',
        'other': 'Autre'
    }
    payment_labels = [payment_method_names.get(p['payment_method'], p['payment_method']) for p in payment_stats]
    payment_data = [float(p['total'] or 0) for p in payment_stats]
    payment_codes = [p['payment_method'] or 'other' for p in payment_stats]

    # 3. Hourly sales pattern (today)
    # Bucket by local hour in Python so this works identically across database
    # backends (MySQL/SQLite) and respects the configured timezone, instead of
    # relying on a backend-specific SQL EXTRACT() expression.
    hourly_labels = list(range(6, 22))  # 6 AM to 9 PM
    hourly_data = [0] * len(hourly_labels)

    for sale in today_sales.values('created_at', 'total_amount'):
        local_hour = timezone.localtime(sale['created_at']).hour
        if 6 <= local_hour < 22:
            hourly_data[local_hour - 6] += float(sale['total_amount'] or 0)

    # 4. Top products sold today
    top_products = SaleItem.objects.filter(
        sale__in=today_sales
    ).values(
        'product__id', 'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('-quantity')[:10]

    # 5. Recent sales (last 20)
    recent_sales = sales_qs.order_by('-created_at')[:20]

    # 6. Cashier performance (today) - only for managers
    cashier_stats = []
    if user.role in ['admin', 'owner', 'manager']:
        cashier_stats = today_sales.values(
            'user__id', 'user__first_name', 'user__last_name', 'user__username'
        ).annotate(
            sales_count=Count('id'),
            sales_total=Sum('total_amount')
        ).order_by('-sales_total')

    context = {
        # Stats
        'today_stats': today_stats,
        'week_stats': week_stats,
        'month_stats': month_stats,
        # Credit tracking
        'today_collected': today_collected,
        'today_credit_given': today_credit_given,
        'today_repayments': today_repayments,
        'credit_outstanding': credit_outstanding,
        'credit_debtors': credit_debtors,
        # Tables
        'recent_sales': recent_sales,
        'top_products': top_products,
        'cashier_stats': cashier_stats,
        # Chart data (JSON)
        'trend_labels': json.dumps(trend_labels),
        'trend_dates': json.dumps(trend_dates),
        'trend_data': json.dumps(trend_data),
        'trend_count': json.dumps(trend_count),
        'payment_labels': json.dumps(payment_labels),
        'payment_data': json.dumps(payment_data),
        'payment_codes': json.dumps(payment_codes),
        'hourly_labels': json.dumps([f'{h}:00' for h in hourly_labels]),
        'hourly_data': json.dumps(hourly_data),
    }

    return render(request, 'pos/dashboard.html', context)


@login_required
def cashier_view(request):
    """
    Main POS cashier interface - Only for cashiers and boutique managers
    Admin/Owner should use Reports for oversight, not operate the cash register
    """
    # Check user role - Only cashiers and boutique managers can use POS
    if request.user.role not in ['boutique_manager', 'cashier']:
        messages.error(request, "L'interface caisse est réservée aux caissiers et gérants de boutique")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = getattr(user, 'location', None)

    # Get categories with product counts
    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('name')

    # Get popular products with stock info
    popular_products = Product.objects.filter(
        is_popular=True,
        is_active=True
    ).select_related('category').prefetch_related('stock_info')[:16]

    # Add stock quantity to each product
    products_with_stock = []
    for product in popular_products:
        # Get stock for user's location or total stock
        stock_qs = product.stock_info.all()
        if location:
            stock_qs = stock_qs.filter(location=location)
        elif enterprise:
            stock_qs = stock_qs.filter(enterprise=enterprise)

        stock = stock_qs.aggregate(total=Sum('quantity'))['total'] or 0
        product.current_stock = float(stock)
        product.is_low_stock = stock <= product.min_stock_threshold
        product.is_out_of_stock = stock <= 0
        products_with_stock.append(product)

    # Get customers for dropdown
    customers = Customer.objects.filter(is_active=True)
    if enterprise:
        customers = customers.filter(enterprise=enterprise)
    customers = customers[:100]

    context = {
        'categories': categories,
        'popular_products': products_with_stock,
        'customers': customers,
        'user_location': location,
    }

    return render(request, 'pos/cashier.html', context)


@login_required
def search_products(request):
    """
    HTMX endpoint to search products with improved fuzzy search
    """
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    popular_only = request.GET.get('popular') == '1'

    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = getattr(user, 'location', None)

    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('stock_info')

    # If requesting popular products only (for refresh after sale)
    if popular_only and not query and not category_id:
        products = products.filter(is_popular=True)[:16]
    else:
        # Normal search/filter logic
        if query:
            # Split query into terms for better matching
            # e.g., "Coca Cola" will match "Coca-Cola", "Coca Cola", etc.
            terms = query.split()

            # Build Q objects for each term
            q_objects = Q()
            for term in terms:
                term_q = (
                    Q(name__icontains=term) |
                    Q(barcode__icontains=term) |
                    Q(sku__icontains=term) |
                    Q(category__name__icontains=term) |
                    Q(description__icontains=term)
                )
                q_objects &= term_q  # All terms must match (AND)

            # Also search for the full query as-is
            full_query_q = (
                Q(name__icontains=query) |
                Q(barcode__icontains=query) |
                Q(sku__icontains=query)
            )

            products = products.filter(q_objects | full_query_q).distinct()

        if category_id:
            products = products.filter(category_id=category_id)

        products = products[:24]

    # Add stock info to each product
    products_with_stock = []
    for product in products:
        stock_qs = product.stock_info.all()
        if location:
            stock_qs = stock_qs.filter(location=location)
        elif enterprise:
            stock_qs = stock_qs.filter(enterprise=enterprise)

        stock = stock_qs.aggregate(total=Sum('quantity'))['total'] or 0
        product.current_stock = float(stock)
        product.is_low_stock = stock <= product.min_stock_threshold
        product.is_out_of_stock = stock <= 0
        products_with_stock.append(product)

    return render(request, 'pos/partials/product_grid.html', {'products': products_with_stock})


@login_required
def create_sale_view(request):
    """
    Create a new sale from cart data
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        import json
        data = json.loads(request.body)

        # Get user's enterprise and location
        user = request.user
        enterprise = getattr(user, 'enterprise', None)
        location = getattr(user, 'location', None)

        # Create sale with enterprise and location
        sale = Sale.objects.create(
            sale_number=Sale.generate_sale_number(),
            customer_id=data.get('customer_id'),
            user=user,
            enterprise=enterprise,
            location=location,
            subtotal=Decimal(str(data.get('subtotal', 0))),
            discount_amount=Decimal(str(data.get('discount_amount', 0))),
            discount_percent=Decimal(str(data.get('discount_percent', 0))),
            tax_amount=Decimal(str(data.get('tax_amount', 0))),
            total_amount=Decimal(str(data.get('total_amount', 0))),
            amount_paid=Decimal(str(data.get('amount_paid', 0))),
            change_amount=Decimal(str(data.get('change_amount', 0))),
            payment_method=data.get('payment_method', 'cash'),
            status='completed'
        )
        
        # Create sale items
        for item in data.get('items', []):
            product = Product.objects.get(id=item['product_id'])
            SaleItem.objects.create(
                sale=sale,
                product=product,
                product_name=product.name,
                quantity=Decimal(str(item['quantity'])),
                unit_price=Decimal(str(item['unit_price'])),
                purchase_price=product.purchase_price,
                discount_amount=Decimal(str(item.get('discount', 0))),
                tax_rate=Decimal(str(item.get('tax_rate', 0))),
                tax_amount=Decimal(str(item.get('tax_amount', 0))),
                total_price=Decimal(str(item['total_price']))
            )
        
        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'sale_number': sale.sale_number,
            'message': f'Vente {sale.sale_number} créée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def sale_receipt_pdf(request, sale_id):
    """
    Generate PDF receipt for a sale.
    Query params: format (A4 or thermal)
    """
    if request.user.role not in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier']:
        return HttpResponse('Accès non autorisé', status=403)
    
    sale = get_object_or_404(Sale, id=sale_id)
    format_type = request.GET.get('format', 'A4')
    
    # Generate PDF
    pdf_buffer = generate_receipt_pdf(sale, format=format_type)
    
    # Return PDF response
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Recu_{sale.sale_number}.pdf"'
    
    # Log receipt generation
    from apps.accounts.models import ActionLog
    ActionLog.objects.create(
        user=request.user,
        action_type='create',
        entity_type='receipt',
        entity_id=sale.id,
        description=f'Reçu généré pour vente {sale.sale_number}'
    )

    return response


@login_required
def create_customer_view(request):
    """
    Create a new customer from POS interface.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if request.user.role not in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)

    try:
        data = json.loads(request.body)

        if not data.get('name'):
            return JsonResponse({'error': 'Le nom est requis'}, status=400)

        # Get user's enterprise
        enterprise = getattr(request.user, 'enterprise', None)

        # Create customer
        customer = Customer.objects.create(
            name=data.get('name'),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            address=data.get('address', ''),
            enterprise=enterprise,
            is_active=True
        )

        return JsonResponse({
            'success': True,
            'customer_id': customer.id,
            'customer_name': customer.name
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
