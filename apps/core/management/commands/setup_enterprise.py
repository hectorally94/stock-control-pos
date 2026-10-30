from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import Enterprise
from apps.locations.models import Location
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Set up test enterprise with locations and assign users'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Creating test enterprise and locations...')

        # Create or get Enterprise
        enterprise, created = Enterprise.objects.get_or_create(
            code='DEMO-ENT',
            defaults={
                'name': 'Entreprise Demo',
                'address': '123 Avenue de la Paix, Bujumbura',
                'phone': '+257 79 000 000',
                'email': 'contact@demo-enterprise.bi',
                'currency': 'FB',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created enterprise: {enterprise.name}'))
        else:
            self.stdout.write(f'Enterprise already exists: {enterprise.name}')

        # Create Main Warehouse
        warehouse, created = Location.objects.get_or_create(
            enterprise=enterprise,
            code='DEPOT-MAIN',
            defaults={
                'name': 'Dépôt Principal',
                'location_type': 'warehouse',
                'address': 'Zone Industrielle, Bujumbura',
                'phone': '+257 79 000 001',
                'is_main_warehouse': True,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created warehouse: {warehouse.name}'))
        else:
            self.stdout.write(f'Warehouse already exists: {warehouse.name}')

        # Create Boutique 1
        boutique1, created = Location.objects.get_or_create(
            enterprise=enterprise,
            code='BTQ-CENTRE',
            defaults={
                'name': 'Boutique Centre-Ville',
                'location_type': 'boutique',
                'address': 'Avenue de l\'Indépendance, Bujumbura',
                'phone': '+257 79 000 002',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created boutique: {boutique1.name}'))
        else:
            self.stdout.write(f'Boutique already exists: {boutique1.name}')

        # Create Boutique 2
        boutique2, created = Location.objects.get_or_create(
            enterprise=enterprise,
            code='BTQ-NORD',
            defaults={
                'name': 'Boutique Quartier Nord',
                'location_type': 'boutique',
                'address': 'Avenue du Nord, Bujumbura',
                'phone': '+257 79 000 003',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created boutique: {boutique2.name}'))
        else:
            self.stdout.write(f'Boutique already exists: {boutique2.name}')

        # Update existing users to belong to enterprise
        admin_user = User.objects.filter(username='admin').first()
        if admin_user:
            admin_user.enterprise = enterprise
            admin_user.role = 'owner'
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated admin as owner of {enterprise.name}'))

        manager_user = User.objects.filter(username='manager').first()
        if manager_user:
            manager_user.enterprise = enterprise
            manager_user.location = boutique1
            manager_user.role = 'boutique_manager'
            manager_user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated manager as boutique manager of {boutique1.name}'))

        stock_manager = User.objects.filter(username='stock_manager').first()
        if stock_manager:
            stock_manager.enterprise = enterprise
            stock_manager.location = warehouse
            stock_manager.role = 'warehouse_manager'
            stock_manager.save()
            self.stdout.write(self.style.SUCCESS(f'Updated stock_manager as warehouse manager of {warehouse.name}'))

        cashier_user = User.objects.filter(username='cashier').first()
        if cashier_user:
            cashier_user.enterprise = enterprise
            cashier_user.location = boutique1
            cashier_user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated cashier at {boutique1.name}'))

        accountant_user = User.objects.filter(username='accountant').first()
        if accountant_user:
            accountant_user.enterprise = enterprise
            accountant_user.save()
            self.stdout.write(self.style.SUCCESS(f'Updated accountant for {enterprise.name}'))

        # Update existing products to belong to enterprise
        from apps.products.models import Product, Category
        updated_categories = Category.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        updated_products = Product.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        self.stdout.write(f'Updated {updated_categories} categories and {updated_products} products')

        # Update existing customers
        from apps.customers.models import Customer
        updated_customers = Customer.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        self.stdout.write(f'Updated {updated_customers} customers')

        # Update existing stock to main warehouse
        from apps.stock.models import Stock, StockMovement
        updated_stock = Stock.objects.filter(enterprise__isnull=True).update(
            enterprise=enterprise,
            location=warehouse
        )
        updated_movements = StockMovement.objects.filter(enterprise__isnull=True).update(
            enterprise=enterprise,
            location=warehouse
        )
        self.stdout.write(f'Updated {updated_stock} stock records and {updated_movements} movements')

        # Update existing sales to boutique 1
        from apps.pos.models import Sale
        updated_sales = Sale.objects.filter(enterprise__isnull=True).update(
            enterprise=enterprise,
            location=boutique1
        )
        self.stdout.write(f'Updated {updated_sales} sales')

        # Update accounting records
        from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession, DailySummary
        ExpenseCategory.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
        Expense.objects.filter(enterprise__isnull=True).update(enterprise=enterprise, location=boutique1)
        CashRegisterSession.objects.filter(enterprise__isnull=True).update(enterprise=enterprise, location=boutique1)
        DailySummary.objects.filter(enterprise__isnull=True).update(enterprise=enterprise, location=boutique1)

        self.stdout.write(self.style.SUCCESS('\nSetup complete!'))
        self.stdout.write(f'\nEnterprise: {enterprise.name} ({enterprise.code})')
        self.stdout.write(f'Locations:')
        self.stdout.write(f'  - {warehouse.name} ({warehouse.code}) - Warehouse')
        self.stdout.write(f'  - {boutique1.name} ({boutique1.code}) - Boutique')
        self.stdout.write(f'  - {boutique2.name} ({boutique2.code}) - Boutique')
