from django.core.management.base import BaseCommand
from apps.accounting.models import ExpenseCategory
from apps.settings.models import StoreSetting


class Command(BaseCommand):
    help = 'Populate default expense categories and store settings'

    # Rôle : crée si absents 9 catégories de dépenses et les paramètres du magasin ; relançable sans doublon.
    # Liens : python manage.py seed_data ; écrit ExpenseCategory et StoreSetting (apps/settings/models.py).
    # Les clés loyalty_* créées ici sont lues par apps/customers/signals.py.
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))
        
        # Create default expense categories
        self.stdout.write('Creating expense categories...')
        categories = [
            ('Rent', 'Monthly rent or lease payments'),
            ('Utilities', 'Electricity, water, internet'),
            ('Salaries', 'Employee wages and salaries'),
            ('Supplies', 'Office and store supplies'),
            ('Transport', 'Transportation and delivery costs'),
            ('Marketing', 'Advertising and promotional expenses'),
            ('Maintenance', 'Equipment and facility maintenance'),
            ('Taxes', 'Business taxes and fees'),
            ('Other', 'Miscellaneous expenses'),
        ]
        
        for name, description in categories:
            category, created = ExpenseCategory.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created category: {name}'))
            else:
                self.stdout.write(f'  - Category already exists: {name}')
        
        # Create default store settings
        self.stdout.write('\nCreating store settings...')
        settings = [
            ('store_name', 'Ma Boutique'),
            ('store_address', ''),
            ('store_phone', ''),
            ('store_email', ''),
            ('store_logo', ''),
            ('store_website', ''),
            ('currency_code', 'XOF'),
            ('currency_symbol', 'FB'),
            ('default_tax_rate', '0'),
            ('date_format', 'DD/MM/YYYY'),
            ('time_format', '24h'),
            ('receipt_header', ''),
            ('receipt_footer', 'Merci pour votre achat!'),
            ('receipt_show_logo', 'true'),
            ('language', 'fr'),
            ('low_stock_alert', 'true'),
            ('allow_negative_stock', 'false'),
            ('auto_backup', 'true'),
            ('backup_frequency', 'daily'),
            ('loyalty_program_enabled', 'false'),
            ('loyalty_points_rate', '1000'),
        ]
        
        for key, value in settings:
            setting, created = StoreSetting.objects.get_or_create(
                key=key,
                defaults={'value': value}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created setting: {key} = {value}'))
            else:
                self.stdout.write(f'  - Setting already exists: {key}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Data seeding completed successfully!'))
