"""
Role-specific dashboards.

Four tableaux de bord, each visible only to the roles it serves:

    Patron        -> admin, owner          (enterprise-wide executive view)
    Gérant        -> manager, boutique_manager (operations; location-scoped for bm)
    Caisse        -> cashier               (personal daily view)
    Comptabilité  -> accountant            (finance, read-only)

`home_dashboard` (the "/" route) dispatches each user to their own dashboard.
Stock-only roles (warehouse_manager, stock_manager) have no bespoke dashboard
and are sent to the existing stock dashboard instead.
"""
import calendar
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.pos.models import Sale, SaleItem
from apps.stock.models import Stock, StockMovement
from apps.transfers.models import Transfer
from apps.locations.models import Location
from apps.accounting.models import Expense, CashRegisterSession
from apps.customers.models import CustomerCredit, CreditPayment


# --- role → dashboard routing -------------------------------------------------

# Which roles each dashboard serves. A user opening a dashboard they don't own
# is bounced to their own (see `_guard`).
DASHBOARD_ROLES = {
    'dashboards:patron': ['admin', 'owner'],
    'dashboards:gerant': ['manager', 'boutique_manager'],
    'dashboards:caisse': ['cashier'],
    'dashboards:comptable': ['accountant'],
}

MONTHS_FR = ['jan', 'fév', 'mar', 'avr', 'mai', 'juin',
             'juil', 'aoû', 'sep', 'oct', 'nov', 'déc']


def dashboard_url_for(user):
    """Return the URL of the dashboard that is *home* for this user's role."""
    role = getattr(user, 'role', None)
    for name, roles in DASHBOARD_ROLES.items():
        if role in roles:
            return reverse(name)
    # Stock-only roles land on the stock dashboard; everyone else on the POS one.
    if role in ('warehouse_manager', 'stock_manager'):
        return reverse('stock:dashboard')
    return reverse('pos:dashboard')


def _guard(request, dashboard_name):
    """If the user's role may not see `dashboard_name`, redirect them home.

    Returns an HttpResponseRedirect to redirect, or None to proceed.
    """
    allowed = DASHBOARD_ROLES.get(dashboard_name, [])
    if getattr(request.user, 'role', None) not in allowed:
        return redirect(dashboard_url_for(request.user))
    return None


# --- shared helpers -----------------------------------------------------------

def _month_start(d):
    return d.replace(day=1)


def _last_months(today, n):
    """List of (year, month, label) for the last `n` months, oldest first."""
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append((y, m, MONTHS_FR[m - 1]))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _sales_month_series(sales_qs, today, n=6):
    """Monthly sales totals (in FB) for the last n months, oldest first."""
    labels, data = [], []
    for y, m, label in _last_months(today, n):
        total = sales_qs.filter(
            created_at__year=y, created_at__month=m
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        labels.append(label)
        data.append(float(total))
    return labels, data


def _month_periods(today, n=6):
    """(start_iso, end_iso) for the last n months, oldest first — for drill-downs."""
    out = []
    for y, m, _ in _last_months(today, n):
        last = calendar.monthrange(y, m)[1]
        out.append({'start': f'{y}-{m:02d}-01', 'end': f'{y}-{m:02d}-{last:02d}'})
    return out


def _cogs(items_qs):
    """Cost of goods sold for a SaleItem queryset."""
    total = Decimal('0')
    for pp, qty in items_qs.values_list('purchase_price', 'quantity'):
        total += (pp or 0) * (qty or 0)
    return total


# ============================================================================
# Home dispatcher
# ============================================================================

@login_required
def home_dashboard(request):
    """Send each user to the dashboard that fits their role."""
    if not getattr(request.user, 'enterprise', None):
        # No enterprise yet — show the simple landing (kept for onboarding).
        return render(request, 'home.html', {
            'today_sales_total': Decimal('0'), 'today_sales_count': 0,
            'total_products': 0, 'low_stock_count': 0, 'pending_transfers': 0,
        })
    return redirect(dashboard_url_for(request.user))


# ============================================================================
# Patron — enterprise-wide executive view
# ============================================================================

@login_required
def patron_dashboard(request):
    bounce = _guard(request, 'dashboards:patron')
    if bounce:
        return bounce

    enterprise = request.user.enterprise
    today = timezone.now().date()
    month_start = _month_start(today)

    completed = Sale.objects.filter(enterprise=enterprise, status='completed')
    month_sales = completed.filter(created_at__date__gte=month_start)

    revenue_month = month_sales.aggregate(t=Sum('total_amount'))['t'] or Decimal('0')
    month_items = SaleItem.objects.filter(
        sale__enterprise=enterprise, sale__status='completed',
        sale__created_at__date__gte=month_start,
    )
    profit_month = revenue_month - _cogs(month_items)

    # Stock value = Σ quantity × purchase price (enterprise-wide)
    stock_value = Decimal('0')
    product_refs = 0
    for qty, pp in Stock.objects.filter(enterprise=enterprise).values_list(
        'quantity', 'product__purchase_price'
    ):
        if qty:
            stock_value += (qty or 0) * (pp or 0)
            product_refs += 1

    credit_outstanding = CustomerCredit.objects.filter(
        customer__enterprise=enterprise, status__in=['pending', 'partial']
    ).aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
    credit_customers = CustomerCredit.objects.filter(
        customer__enterprise=enterprise, status__in=['pending', 'partial']
    ).values('customer').distinct().count()

    # CA — 6 last months (+ periods so chart bars can drill into sales_list)
    ca_labels, ca_data = _sales_month_series(completed, today, 6)
    ca_periods = _month_periods(today, 6)

    # Sales by location (this month) — id kept so each row links to filtered sales
    by_loc = list(
        month_sales.values('location__id', 'location__name')
        .annotate(total=Sum('total_amount'))
        .order_by('-total')[:6]
    )
    max_loc = max((r['total'] or 0 for r in by_loc), default=0) or 1
    sales_by_location = [{
        'id': r['location__id'],
        'name': r['location__name'] or 'Sans emplacement',
        'total': float(r['total'] or 0),
        'pct': round(float(r['total'] or 0) / float(max_loc) * 100),
    } for r in by_loc]

    # Top products (this month) by revenue — id kept so each row links to product detail
    top_products = list(
        month_items.values('product__id', 'product__name')
        .annotate(revenue=Sum('total_price'), qty=Sum('quantity'))
        .order_by('-revenue')[:5]
    )

    # Stock alerts count
    low = out = 0
    for s in Stock.objects.filter(enterprise=enterprise).select_related('product'):
        if s.quantity <= 0:
            out += 1
        elif s.is_low_stock:
            low += 1

    context = {
        'kpi_revenue': revenue_month,
        'kpi_profit': profit_month,
        'kpi_stock_value': stock_value,
        'kpi_product_refs': product_refs,
        'kpi_credit': credit_outstanding,
        'kpi_credit_customers': credit_customers,
        'ca_labels': ca_labels,
        'ca_data': ca_data,
        'ca_periods': ca_periods,
        'sales_by_location': sales_by_location,
        'top_products': top_products,
        'alert_low': low,
        'alert_out': out,
        'link_credits': reverse('customers:credit_list'),
        'link_reports': reverse('reports:dashboard'),
        'link_low': reverse('stock:low_stock'),
        'link_out': reverse('stock:out_of_stock'),
        'link_sales': reverse('pos:sales_list') + '?date=month',
        'sales_base': reverse('pos:sales_list'),
    }
    return render(request, 'dashboards/patron.html', context)


# ============================================================================
# Gérant — operations (location-scoped for boutique managers)
# ============================================================================

@login_required
def gerant_dashboard(request):
    bounce = _guard(request, 'dashboards:gerant')
    if bounce:
        return bounce

    user = request.user
    enterprise = user.enterprise
    location = getattr(user, 'location', None)
    today = timezone.now().date()
    month_start = _month_start(today)

    scoped = location if user.role == 'boutique_manager' else None

    completed = Sale.objects.filter(enterprise=enterprise, status='completed')
    if scoped:
        completed = completed.filter(location=scoped)

    today_sales = completed.filter(created_at__date=today).aggregate(
        total=Sum('total_amount'), count=Count('id')
    )

    transfers = Transfer.objects.filter(enterprise=enterprise)
    if scoped:
        transfers = transfers.filter(
            Q(source_location=scoped) | Q(destination_location=scoped)
        )
    pending_transfers = transfers.filter(status__in=['pending', 'in_transit']).count()

    # Stock health
    stock_qs = Stock.objects.filter(enterprise=enterprise).select_related('product', 'location')
    if scoped:
        stock_qs = stock_qs.filter(location=scoped)
    low = out = 0
    low_items = []
    for s in stock_qs:
        if s.quantity <= 0:
            out += 1
        elif s.is_low_stock:
            low += 1
            if len(low_items) < 6:
                low_items.append(s)

    expenses = Expense.objects.filter(enterprise=enterprise)
    if scoped:
        expenses = expenses.filter(location=scoped)
    month_expenses = expenses.filter(expense_date__gte=month_start).aggregate(
        total=Sum('amount'), count=Count('id')
    )

    # Sales — last 14 days
    labels, data, iso = [], [], []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        total = completed.filter(created_at__date=day).aggregate(t=Sum('total_amount'))['t'] or 0
        labels.append(day.strftime('%d/%m'))
        iso.append(day.isoformat())
        data.append(float(total))

    recent_sales = completed.select_related('user', 'location', 'customer').order_by('-created_at')[:8]

    context = {
        'scoped_location': scoped,
        'kpi_today_total': today_sales['total'] or Decimal('0'),
        'kpi_today_count': today_sales['count'] or 0,
        'kpi_pending_transfers': pending_transfers,
        'kpi_low': low,
        'kpi_out': out,
        'kpi_month_expenses': month_expenses['total'] or Decimal('0'),
        'kpi_expense_count': month_expenses['count'] or 0,
        'sales_labels': labels,
        'sales_data': data,
        'sales_iso': iso,
        'low_items': low_items,
        'recent_sales': recent_sales,
        'link_transfers': reverse('transfers:list'),
        'link_low': reverse('stock:low_stock'),
        'link_expenses': reverse('accounting:expense_list'),
        'link_sales': reverse('pos:sales_list') + '?date=today',
    }
    return render(request, 'dashboards/gerant.html', context)


# ============================================================================
# Caisse — cashier's personal day
# ============================================================================

@login_required
def caisse_dashboard(request):
    bounce = _guard(request, 'dashboards:caisse')
    if bounce:
        return bounce

    user = request.user
    enterprise = user.enterprise
    location = getattr(user, 'location', None)
    today = timezone.now().date()

    my_sales_today = Sale.objects.filter(
        enterprise=enterprise, status='completed', user=user, created_at__date=today
    )
    stats = my_sales_today.aggregate(total=Sum('total_amount'), count=Count('id'))
    my_total = stats['total'] or Decimal('0')
    my_count = stats['count'] or 0
    avg_basket = (my_total / my_count) if my_count else Decimal('0')

    # Current cash session for this user
    session = CashRegisterSession.objects.filter(
        enterprise=enterprise, user=user
    ).order_by('-opened_at').first()
    session_open = bool(session and session.status == 'open')

    # Credit granted today (credit-payment sales by this user)
    credit_today = my_sales_today.filter(payment_method='credit').aggregate(
        t=Sum('total_amount'), c=Count('id')
    )

    # Sales by hour (today) — bucketed in Python for DB portability
    hours = list(range(7, 21))  # 07h..20h
    hour_counts = {h: 0.0 for h in hours}
    for s in my_sales_today.only('created_at', 'total_amount'):
        h = timezone.localtime(s.created_at).hour
        if h in hour_counts:
            hour_counts[h] += float(s.total_amount)
    hour_labels = [f'{h}h' for h in hours]
    hour_data = [hour_counts[h] for h in hours]

    recent = my_sales_today.select_related('customer').order_by('-created_at')[:8]

    context = {
        'kpi_my_total': my_total,
        'kpi_my_count': my_count,
        'kpi_avg_basket': avg_basket,
        'session': session,
        'session_open': session_open,
        'kpi_credit_total': credit_today['t'] or Decimal('0'),
        'kpi_credit_count': credit_today['c'] or 0,
        'hour_labels': hour_labels,
        'hour_data': hour_data,
        'recent_sales': recent,
        'user_location': location,
        'link_pos': reverse('pos:cashier'),
        'link_sessions': reverse('accounting:cash_session_list'),
        'link_my_sales': reverse('pos:dashboard'),
    }
    return render(request, 'dashboards/caisse.html', context)


# ============================================================================
# Comptabilité — finance (read-only, enterprise-wide)
# ============================================================================

@login_required
def comptable_dashboard(request):
    bounce = _guard(request, 'dashboards:comptable')
    if bounce:
        return bounce

    enterprise = request.user.enterprise
    today = timezone.now().date()
    month_start = _month_start(today)

    completed = Sale.objects.filter(enterprise=enterprise, status='completed')
    revenue_month = completed.filter(created_at__date__gte=month_start).aggregate(
        t=Sum('total_amount'))['t'] or Decimal('0')
    month_items = SaleItem.objects.filter(
        sale__enterprise=enterprise, sale__status='completed',
        sale__created_at__date__gte=month_start,
    )
    profit_month = revenue_month - _cogs(month_items)
    margin = (profit_month / revenue_month * 100) if revenue_month else Decimal('0')

    expenses = Expense.objects.filter(enterprise=enterprise)
    expenses_month = expenses.filter(expense_date__gte=month_start).aggregate(
        t=Sum('amount'))['t'] or Decimal('0')

    credit_outstanding = CustomerCredit.objects.filter(
        customer__enterprise=enterprise, status__in=['pending', 'partial']
    ).aggregate(t=Sum('remaining_amount'))['t'] or Decimal('0')
    credit_customers = CustomerCredit.objects.filter(
        customer__enterprise=enterprise, status__in=['pending', 'partial']
    ).values('customer').distinct().count()

    # Revenus vs Dépenses — 6 months (+ periods for chart-bar drill-down)
    labels, rev_series, exp_series = [], [], []
    for y, m, label in _last_months(today, 6):
        rev = completed.filter(created_at__year=y, created_at__month=m).aggregate(
            t=Sum('total_amount'))['t'] or 0
        exp = expenses.filter(expense_date__year=y, expense_date__month=m).aggregate(
            t=Sum('amount'))['t'] or 0
        labels.append(label)
        rev_series.append(float(rev))
        exp_series.append(float(exp))
    rev_exp_periods = _month_periods(today, 6)

    # Expenses by category (this month) — id kept so each row links to filtered expenses
    by_cat = list(
        expenses.filter(expense_date__gte=month_start)
        .values('expense_category__id', 'expense_category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')[:6]
    )
    cat_labels = [c['expense_category__name'] or 'Non catégorisé' for c in by_cat]
    cat_data = [float(c['total'] or 0) for c in by_cat]
    cat_ids = [c['expense_category__id'] for c in by_cat]

    # Cash sessions to reconcile (recently closed, with a difference)
    sessions = CashRegisterSession.objects.filter(
        enterprise=enterprise, status='closed'
    ).select_related('user', 'location').order_by('-closed_at')[:6]

    context = {
        'kpi_revenue': revenue_month,
        'kpi_expenses': expenses_month,
        'kpi_profit': profit_month,
        'kpi_margin': margin,
        'kpi_credit': credit_outstanding,
        'kpi_credit_customers': credit_customers,
        'rev_exp_labels': labels,
        'rev_series': rev_series,
        'exp_series': exp_series,
        'rev_exp_periods': rev_exp_periods,
        'cat_labels': cat_labels,
        'cat_data': cat_data,
        'cat_rows': list(zip(cat_labels, cat_data, cat_ids)),
        'sessions': sessions,
        'link_expenses': reverse('accounting:expense_list'),
        'link_reports': reverse('reports:dashboard'),
        'link_credits': reverse('customers:credit_list'),
        'link_sessions': reverse('accounting:cash_session_list'),
        'expenses_base': reverse('accounting:expense_list'),
        'sales_base': reverse('pos:sales_list'),
    }
    return render(request, 'dashboards/comptable.html', context)
