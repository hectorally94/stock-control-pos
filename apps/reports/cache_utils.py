"""
Caching utilities for reports and dashboards
"""
from django.core.cache import cache
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.pos.models import Sale, SaleItem
from apps.accounting.models import Expense, DailySummary
from apps.stock.models import Stock
from apps.customers.models import Customer


def get_dashboard_stats(force_refresh=False):
    """
    Get cached dashboard statistics
    Cache for 5 minutes
    """
    cache_key = 'dashboard_stats'
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
    
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    # Today's sales
    today_sales = Sale.objects.filter(
        created_at__date=today,
        status='completed'
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Month's sales
    month_sales = Sale.objects.filter(
        created_at__date__gte=month_start,
        status='completed'
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Month's expenses
    month_expenses = Expense.objects.filter(
        expense_date__gte=month_start
    ).aggregate(
        total=Sum('amount')
    )
    
    # Low stock products
    low_stock_count = Stock.objects.filter(
        quantity__lte=F('product__min_stock_threshold')
    ).count()
    
    # Customers with credit
    customers_with_credit = Customer.objects.filter(
        current_balance__gt=0
    ).count()
    
    data = {
        'today_sales': {
            'total': today_sales['total'] or Decimal('0.00'),
            'count': today_sales['count'] or 0
        },
        'month_sales': {
            'total': month_sales['total'] or Decimal('0.00'),
            'count': month_sales['count'] or 0
        },
        'month_expenses': {
            'total': month_expenses['total'] or Decimal('0.00')
        },
        'low_stock_count': low_stock_count,
        'customers_with_credit': customers_with_credit,
        'last_updated': timezone.now().isoformat()
    }
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 300)
    
    return data


def get_sales_summary(start_date, end_date, force_refresh=False):
    """
    Get cached sales summary for date range
    Cache for 10 minutes
    """
    cache_key = f'sales_summary_{start_date}_{end_date}'
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
    
    sales = Sale.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        status='completed'
    )
    
    summary = {
        'total_sales': sales.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00'),
        'count': sales.count(),
        'by_payment_method': {},
        'by_day': []
    }
    
    # Payment method breakdown
    for method, label in Sale.PAYMENT_METHOD_CHOICES:
        method_total = sales.filter(payment_method=method).aggregate(
            Sum('total_amount')
        )['total_amount__sum'] or Decimal('0.00')
        summary['by_payment_method'][method] = {
            'label': label,
            'total': method_total
        }
    
    # Daily breakdown
    from django.db.models.functions import TruncDate
    daily_sales = sales.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('date')
    
    summary['by_day'] = list(daily_sales)
    
    # Cache for 10 minutes
    cache.set(cache_key, summary, 600)
    
    return summary


def get_top_products(limit=10, days=30, force_refresh=False):
    """
    Get cached top selling products
    Cache for 15 minutes
    """
    cache_key = f'top_products_{days}_{limit}'
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
    
    start_date = timezone.now().date() - timedelta(days=days)
    
    from django.db.models import F
    top_products = SaleItem.objects.filter(
        sale__created_at__date__gte=start_date,
        sale__status='completed'
    ).values(
        'product__name',
        'product__id'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price'),
        total_profit=Sum(F('unit_price') * F('quantity') - F('purchase_price') * F('quantity'))
    ).order_by('-total_revenue')[:limit]
    
    data = list(top_products)
    
    # Cache for 15 minutes
    cache.set(cache_key, data, 900)
    
    return data


def invalidate_dashboard_cache():
    """Invalidate all dashboard caches"""
    cache.delete('dashboard_stats')
    # Invalidate other related caches
    cache.delete_pattern('sales_summary_*')
    cache.delete_pattern('top_products_*')


def get_stock_alerts(force_refresh=False):
    """
    Get cached stock alerts
    Cache for 10 minutes
    """
    cache_key = 'stock_alerts'
    
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
    
    from django.db.models import F
    
    low_stock = Stock.objects.filter(
        quantity__gt=0,
        quantity__lte=F('product__min_stock_threshold')
    ).select_related('product', 'product__category').order_by('quantity')[:20]
    
    out_of_stock = Stock.objects.filter(
        quantity=0
    ).select_related('product', 'product__category').order_by('product__name')[:20]
    
    data = {
        'low_stock': list(low_stock.values(
            'product__id',
            'product__name',
            'product__category__name',
            'quantity',
            'product__min_stock_threshold'
        )),
        'out_of_stock': list(out_of_stock.values(
            'product__id',
            'product__name',
            'product__category__name'
        ))
    }
    
    # Cache for 10 minutes
    cache.set(cache_key, data, 600)
    
    return data

