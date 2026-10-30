"""
Views for Reports Dashboard
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, F, Avg
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from apps.pos.models import Sale, SaleItem
from apps.accounting.models import DailySummary, Expense
from apps.products.models import Product, Category
from apps.locations.models import Location, LocationStock
from apps.reports.utils.excel_generator import sales_report, inventory_report, expense_report, customer_report


# Rôle : calcule ventes, dépenses, bénéfice, crédits, stock par emplacement et données JSON des graphiques.
# Liens : route /reports/ ; template apps/reports/templates/reports/dashboard.html ;
# lit Sale, SaleItem, Expense, CustomerCredit, CreditPayment, Location et LocationStock.
@login_required
def dashboard_view(request):
    """Reports dashboard with charts"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    # Get today's sales
    today = timezone.now().date()
    today_sales = Sale.objects.filter(
        created_at__date=today,
        status='completed'
    )
    if enterprise:
        today_sales = today_sales.filter(enterprise=enterprise)

    today_stats = today_sales.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    # Get this month's summary
    month_start = today.replace(day=1)
    month_sales = Sale.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    )
    if enterprise:
        month_sales = month_sales.filter(enterprise=enterprise)

    month_stats = month_sales.aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )

    month_expenses = Expense.objects.filter(
        expense_date__gte=month_start
    )
    if enterprise:
        month_expenses = month_expenses.filter(enterprise=enterprise)

    expense_stats = month_expenses.aggregate(
        total=Sum('amount')
    )

    # Calculate profit
    revenue = month_stats['total'] or Decimal('0')
    expenses = expense_stats['total'] or Decimal('0')
    profit = revenue - expenses

    # --- CREDIT TRACKING (vendu vs encaissé vs crédit, ce mois) ---
    from apps.customers.models import CustomerCredit, CreditPayment
    credits_qs = CustomerCredit.objects.all()
    payments_qs = CreditPayment.objects.all()
    if enterprise:
        credits_qs = credits_qs.filter(customer__enterprise=enterprise)
        payments_qs = payments_qs.filter(credit__customer__enterprise=enterprise)

    month_credit_given = credits_qs.filter(created_at__date__gte=month_start).aggregate(
        t=Sum('original_amount'))['t'] or Decimal('0')
    month_repayments = payments_qs.filter(created_at__date__gte=month_start).aggregate(
        t=Sum('amount'))['t'] or Decimal('0')
    month_collected = revenue - month_credit_given + month_repayments

    open_credits = credits_qs.filter(status__in=['pending', 'partial'])
    credit_outstanding = open_credits.aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
    credit_debtors = open_credits.values('customer').distinct().count()

    # --- CHART DATA ---

    # 1. Daily sales for the last 7 days
    last_7_days = []
    daily_dates = []  # ISO dates so chart points can link to that day's sales
    daily_sales_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        last_7_days.append(day.strftime('%d/%m'))
        daily_dates.append(day.isoformat())

        day_sales = Sale.objects.filter(
            created_at__date=day,
            status='completed'
        )
        if enterprise:
            day_sales = day_sales.filter(enterprise=enterprise)

        total = day_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        daily_sales_data.append(float(total))

    # 2. Monthly sales for the last 6 months
    monthly_labels = []
    monthly_ranges = []  # start/end of each month for drill-down links
    monthly_sales_data = []
    monthly_expenses_data = []

    for i in range(5, -1, -1):
        month_date = today - timedelta(days=i * 30)
        month_date = month_date.replace(day=1)
        next_month = (month_date + timedelta(days=32)).replace(day=1)

        monthly_labels.append(month_date.strftime('%b %Y'))
        monthly_ranges.append({
            'start': month_date.isoformat(),
            'end': (next_month - timedelta(days=1)).isoformat(),
        })

        m_sales = Sale.objects.filter(
            created_at__date__gte=month_date,
            created_at__date__lt=next_month,
            status='completed'
        )
        if enterprise:
            m_sales = m_sales.filter(enterprise=enterprise)
        total_sales = m_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        monthly_sales_data.append(float(total_sales))

        m_expenses = Expense.objects.filter(
            expense_date__gte=month_date,
            expense_date__lt=next_month
        )
        if enterprise:
            m_expenses = m_expenses.filter(enterprise=enterprise)
        total_expenses = m_expenses.aggregate(total=Sum('amount'))['total'] or 0
        monthly_expenses_data.append(float(total_expenses))

    # 3. Sales by category (top 5)
    category_sales = SaleItem.objects.filter(
        sale__status='completed',
        sale__created_at__date__gte=month_start
    )
    if enterprise:
        category_sales = category_sales.filter(sale__enterprise=enterprise)

    category_data = category_sales.values(
        'product__category__id', 'product__category__name'
    ).annotate(
        total=Sum('total_price')
    ).order_by('-total')[:5]

    category_labels = [c['product__category__name'] or 'Sans catégorie' for c in category_data]
    category_amounts = [float(c['total'] or 0) for c in category_data]
    category_ids = [c['product__category__id'] for c in category_data]

    # 4. Payment methods distribution
    payment_data = Sale.objects.filter(
        status='completed',
        created_at__date__gte=month_start
    )
    if enterprise:
        payment_data = payment_data.filter(enterprise=enterprise)

    payment_stats = payment_data.values('payment_method').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')

    payment_labels = []
    payment_amounts = []
    payment_method_names = {
        'cash': 'Espèces',
        'card': 'Carte',
        'mobile_money': 'Mobile Money',
        'credit': 'Crédit',
        'other': 'Autre'
    }
    payment_codes = []
    for p in payment_stats:
        method = p['payment_method'] or 'other'
        payment_labels.append(payment_method_names.get(method, method))
        payment_amounts.append(float(p['total'] or 0))
        payment_codes.append(method)

    # 5. Top selling products
    top_products = SaleItem.objects.filter(
        sale__status='completed',
        sale__created_at__date__gte=month_start
    )
    if enterprise:
        top_products = top_products.filter(sale__enterprise=enterprise)

    top_products_data = top_products.values(
        'product__id', 'product__name'
    ).annotate(
        quantity=Sum('quantity'),
        revenue=Sum('total_price')
    ).order_by('-quantity')[:10]

    # 6. Stock status by location
    stock_status = []
    if enterprise:
        locations = Location.objects.filter(enterprise=enterprise, is_active=True)
        for loc in locations:
            stock = LocationStock.objects.filter(location=loc)
            total_items = stock.aggregate(total=Sum('quantity'))['total'] or 0
            low_stock = stock.filter(quantity__lte=F('min_stock_threshold')).count()
            stock_status.append({
                'id': loc.id,
                'name': loc.name,
                'type': loc.location_type,
                'total': float(total_items),
                'low': low_stock
            })

    # 7. Hourly sales pattern (today)
    # Bucket by local hour in Python so this works identically across database
    # backends (MySQL/SQLite) and respects the configured timezone, instead of
    # relying on a backend-specific SQL EXTRACT() expression.
    hourly_labels = list(range(6, 22))  # 6 AM to 9 PM
    hourly_data = [0] * len(hourly_labels)
    for sale in today_sales.values('created_at', 'total_amount'):
        local_hour = timezone.localtime(sale['created_at']).hour
        if 6 <= local_hour < 22:
            hourly_data[local_hour - 6] += float(sale['total_amount'] or 0)

    # Locations for the per-store report panel
    report_locations = Location.objects.filter(
        enterprise=enterprise, is_active=True
    ).order_by('location_type', 'name') if enterprise else Location.objects.none()

    context = {
        'report_locations': report_locations,
        'today_sales': today_stats,
        'month_sales': month_stats,
        'month_expenses': expense_stats,
        'profit': profit,
        # Credit tracking
        'month_collected': month_collected,
        'month_credit_given': month_credit_given,
        'month_repayments': month_repayments,
        'credit_outstanding': credit_outstanding,
        'credit_debtors': credit_debtors,
        'start_date': month_start.strftime('%Y-%m-%d'),
        'end_date': today.strftime('%Y-%m-%d'),
        # Chart data (JSON serialized)
        'daily_labels': json.dumps(last_7_days),
        'daily_dates': json.dumps(daily_dates),
        'daily_data': json.dumps(daily_sales_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_ranges': json.dumps(monthly_ranges),
        'monthly_sales': json.dumps(monthly_sales_data),
        'monthly_expenses': json.dumps(monthly_expenses_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_amounts),
        'category_ids': json.dumps(category_ids),
        'payment_labels': json.dumps(payment_labels),
        'payment_data': json.dumps(payment_amounts),
        'payment_codes': json.dumps(payment_codes),
        'top_products': top_products_data,
        'stock_status': stock_status,
        'hourly_labels': json.dumps([f'{h}:00' for h in hourly_labels]),
        'hourly_data': json.dumps(hourly_data),
    }

    return render(request, 'reports/dashboard.html', context)


# Rôle : renvoie en JSON les ventes quotidiennes des 30 derniers jours (seul type accepté : daily).
# Liens : aucune route dans apps/reports/urls.py et aucun appelant trouvé ; lit Sale (apps/pos/models.py).
@login_required
def chart_data_api(request):
    """API endpoint for chart data (AJAX)"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)

    chart_type = request.GET.get('type', 'daily')
    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    today = timezone.now().date()

    if chart_type == 'daily':
        # Last 30 days
        data = []
        labels = []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            labels.append(day.strftime('%d/%m'))

            day_sales = Sale.objects.filter(
                created_at__date=day,
                status='completed'
            )
            if enterprise:
                day_sales = day_sales.filter(enterprise=enterprise)

            total = day_sales.aggregate(total=Sum('total_amount'))['total'] or 0
            data.append(float(total))

        return JsonResponse({'labels': labels, 'data': data})

    return JsonResponse({'error': 'Type non supporté'}, status=400)


# Rôle : télécharge le rapport Excel des ventes (mois en cours par défaut) et journalise l'export.
# Liens : route /reports/export/sales/ (boutons de reports/dashboard.html) ;
# appelle sales_report (apps/reports/utils/excel_generator.py) ; écrit dans ActionLog.
@login_required
def export_sales_report(request):
    """Export sales report to Excel"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        return HttpResponse('Accès non autorisé', status=403)

    # Get date range from query params
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        # Default to current month
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today

    # Get filters
    filters = {}
    if request.GET.get('customer_id'):
        filters['customer_id'] = request.GET.get('customer_id')
    if request.GET.get('cashier_id'):
        filters['cashier_id'] = request.GET.get('cashier_id')
    if request.GET.get('payment_method'):
        filters['payment_method'] = request.GET.get('payment_method')
    if request.GET.get('location'):
        filters['location_id'] = request.GET.get('location')

    # Generate workbook (scoped to the user's enterprise)
    enterprise = getattr(request.user, 'enterprise', None)
    workbook = sales_report(start_date, end_date, filters, enterprise=enterprise)

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=Rapport_Ventes_{start_date}_{end_date}.xlsx'

    # Save workbook to response
    workbook.save(response)

    # Log export
    from apps.accounts.models import ActionLog
    ActionLog.objects.create(
        user=request.user,
        action_type='create',
        entity_type='export',
        description=f'Export Excel des ventes ({start_date} à {end_date})'
    )

    return response


# Rôle : télécharge l'inventaire Excel, éventuellement limité à un emplacement, et journalise l'export.
# Liens : route /reports/export/inventory/ (boutons de reports/dashboard.html) ;
# appelle inventory_report (apps/reports/utils/excel_generator.py) ; écrit dans ActionLog.
@login_required
def export_inventory_report(request):
    """Export inventory report to Excel"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        return HttpResponse('Accès non autorisé', status=403)

    # Generate workbook (scoped to the user's enterprise; optional per-store)
    enterprise = getattr(request.user, 'enterprise', None)
    location = None
    if request.GET.get('location') and enterprise:
        location = Location.objects.filter(
            pk=request.GET.get('location'), enterprise=enterprise
        ).first()
    workbook = inventory_report(enterprise=enterprise, location=location)

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    suffix = f'_{location.code}' if location else ''
    response['Content-Disposition'] = f'attachment; filename=Rapport_Inventaire{suffix}_{datetime.now().strftime("%Y%m%d")}.xlsx'

    # Save workbook to response
    workbook.save(response)

    # Log export
    from apps.accounts.models import ActionLog
    ActionLog.objects.create(
        user=request.user,
        action_type='create',
        entity_type='export',
        description='Export Excel de l\'inventaire'
    )

    return response


# Rôle : télécharge le rapport Excel des dépenses (mois en cours par défaut) et journalise l'export.
# Liens : route /reports/export/expenses/ (bouton de reports/dashboard.html) ;
# appelle expense_report (apps/reports/utils/excel_generator.py) ; écrit dans ActionLog.
@login_required
def export_expense_report(request):
    """Export expense report to Excel"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        return HttpResponse('Accès non autorisé', status=403)

    # Get date range
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        today = timezone.now().date()
        start_date = today.replace(day=1)
        end_date = today

    # Generate workbook (scoped to the user's enterprise)
    workbook = expense_report(start_date, end_date, enterprise=getattr(request.user, 'enterprise', None))

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=Rapport_Depenses_{start_date}_{end_date}.xlsx'

    # Save workbook to response
    workbook.save(response)

    # Log export
    from apps.accounts.models import ActionLog
    ActionLog.objects.create(
        user=request.user,
        action_type='create',
        entity_type='export',
        description=f'Export Excel des dépenses ({start_date} à {end_date})'
    )

    return response


# Rôle : télécharge le rapport Excel des clients et journalise l'export.
# Liens : route /reports/export/customers/ (bouton de reports/dashboard.html) ;
# appelle customer_report (apps/reports/utils/excel_generator.py) ; écrit dans ActionLog.
@login_required
def export_customer_report(request):
    """Export customer report to Excel"""
    if request.user.role not in ['admin', 'owner', 'manager', 'accountant']:
        return HttpResponse('Accès non autorisé', status=403)

    # Generate workbook (scoped to the user's enterprise)
    workbook = customer_report(enterprise=getattr(request.user, 'enterprise', None))

    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=Rapport_Clients_{datetime.now().strftime("%Y%m%d")}.xlsx'

    # Save workbook to response
    workbook.save(response)

    # Log export
    from apps.accounts.models import ActionLog
    ActionLog.objects.create(
        user=request.user,
        action_type='create',
        entity_type='export',
        description='Export Excel des clients'
    )

    return response
