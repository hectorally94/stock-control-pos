"""
Management command to generate/update DailySummary records.

Usage:
    python manage.py generate_daily_summary
    python manage.py generate_daily_summary --date 2025-12-04
    python manage.py generate_daily_summary --backfill 2025-01-01 2025-12-31
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from apps.accounting.models import DailySummary, Expense
from apps.pos.models import Sale, SaleItem
from apps.customers.models import CreditPayment


class Command(BaseCommand):
    help = 'Generate or update daily summary for sales, expenses, and profits'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date to generate summary for (YYYY-MM-DD). Defaults to yesterday.',
        )
        parser.add_argument(
            '--backfill',
            nargs=2,
            metavar=('START_DATE', 'END_DATE'),
            help='Generate summaries for a date range (YYYY-MM-DD YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Determine which dates to process
        if options['backfill']:
            # Backfill mode: process date range
            try:
                start_date = datetime.strptime(options['backfill'][0], '%Y-%m-%d').date()
                end_date = datetime.strptime(options['backfill'][1], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Invalid date format. Use YYYY-MM-DD')
            
            if start_date > end_date:
                raise CommandError('Start date must be before end date')
            
            self.stdout.write(self.style.WARNING(
                f'Backfilling summaries from {start_date} to {end_date}...'
            ))
            
            # Process each date in range
            current_date = start_date
            success_count = 0
            error_count = 0
            
            while current_date <= end_date:
                try:
                    self.generate_summary_for_date(current_date)
                    success_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'✗ Error for {current_date}: {str(e)}'
                    ))
                    error_count += 1
                
                current_date += timedelta(days=1)
            
            self.stdout.write(self.style.SUCCESS(
                f'\nBackfill complete: {success_count} successful, {error_count} errors'
            ))
        
        elif options['date']:
            # Single date mode
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Invalid date format. Use YYYY-MM-DD')
            
            self.generate_summary_for_date(target_date)
        
        else:
            # Default: yesterday
            yesterday = (timezone.now() - timedelta(days=1)).date()
            self.generate_summary_for_date(yesterday)

    def generate_summary_for_date(self, summary_date):
        """Generate summary for a specific date"""
        
        self.stdout.write(f'Processing {summary_date}...')
        
        # Get completed sales for the date
        sales = Sale.objects.filter(
            created_at__date=summary_date,
            status='completed'
        )
        
        # Calculate total sales
        total_sales = sales.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Calculate sales by payment method
        total_cash = sales.filter(payment_method='cash').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_mobile_money = sales.filter(payment_method='mobile_money').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_card = sales.filter(payment_method='card').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        total_credit = sales.filter(payment_method='credit').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Calculate cost of goods sold
        sale_items = SaleItem.objects.filter(
            sale__created_at__date=summary_date,
            sale__status='completed'
        )
        
        total_cost_of_goods = sale_items.aggregate(
            total=Sum(F('purchase_price') * F('quantity'))
        )['total'] or 0
        
        # Calculate credit collected
        credit_collected = CreditPayment.objects.filter(
            created_at__date=summary_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate total expenses
        total_expenses = Expense.objects.filter(
            expense_date=summary_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate metrics
        gross_profit = total_sales - total_cost_of_goods
        net_profit = gross_profit - total_expenses
        
        # Count sales and customers
        number_of_sales = sales.count()
        number_of_customers = sales.filter(
            customer__isnull=False
        ).values('customer').distinct().count()
        
        # Create or update summary
        summary, created = DailySummary.objects.update_or_create(
            summary_date=summary_date,
            defaults={
                'total_sales': total_sales,
                'total_expenses': total_expenses,
                'total_cash': total_cash,
                'total_mobile_money': total_mobile_money,
                'total_card': total_card,
                'total_credit': total_credit,
                'credit_collected': credit_collected,
                'total_cost_of_goods': total_cost_of_goods,
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'number_of_sales': number_of_sales,
                'number_of_customers': number_of_customers,
            }
        )
        
        # Format output
        action = 'créé' if created else 'mis à jour'
        self.stdout.write(self.style.SUCCESS(
            f'✓ Résumé journalier pour {summary_date} {action}'
        ))
        
        # Display summary
        self.stdout.write(f'   Ventes totales: {self._format_currency(total_sales)}')
        self.stdout.write(f'   Dépenses totales: {self._format_currency(total_expenses)}')
        self.stdout.write(f'   Bénéfice brut: {self._format_currency(gross_profit)}')
        self.stdout.write(f'   Bénéfice net: {self._format_currency(net_profit)}')
        self.stdout.write(f'   Nombre de ventes: {number_of_sales}')
        self.stdout.write(f'   Nombre de clients: {number_of_customers}')
        
        # Display payment breakdown
        if total_sales > 0:
            self.stdout.write(f'   Répartition des paiements:')
            if total_cash > 0:
                self.stdout.write(f'     - Espèces: {self._format_currency(total_cash)}')
            if total_mobile_money > 0:
                self.stdout.write(f'     - Mobile Money: {self._format_currency(total_mobile_money)}')
            if total_card > 0:
                self.stdout.write(f'     - Carte: {self._format_currency(total_card)}')
            if total_credit > 0:
                self.stdout.write(f'     - Crédit: {self._format_currency(total_credit)}')
            if credit_collected > 0:
                self.stdout.write(f'   Crédit collecté: {self._format_currency(credit_collected)}')
        
        self.stdout.write('')  # Empty line for readability
    
    def _format_currency(self, amount):
        """Format amount as FB currency"""
        return f'{amount:,.0f} FB'.replace(',', ' ')

