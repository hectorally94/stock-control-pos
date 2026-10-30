"""
Seed a starter product catalog (categories + products) into EXISTING enterprises.

Unlike `seed_full_data` (which creates its own demo enterprise/users), this command
attaches a usable catalog to the enterprise(s) your real users already belong to,
so dropdowns like "Entrée de Stock" are no longer empty.

Idempotent: re-running it will not create duplicates. Products are matched by
(enterprise, sku) and categories by (enterprise, name).

Usage:
    python manage.py seed_catalog                  # all existing enterprises
    python manage.py seed_catalog --enterprise HEMA01
    python manage.py seed_catalog --with-stock     # also create a Stock row (qty 0) per product
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


# (category, name, sku, purchase_price, sale_price, unit, is_popular)
CATALOG = [
    # Boissons
    ('Boissons', 'Coca-Cola 50cl', 'CC-50CL', 800, 1000, 'piece', True),
    ('Boissons', 'Fanta Orange 50cl', 'FO-50CL', 800, 1000, 'piece', True),
    ('Boissons', 'Eau Minerale 1.5L', 'EM-1.5L', 600, 800, 'piece', True),
    ('Boissons', 'Jus Rani Mangue 1L', 'JR-MG-1L', 1800, 2500, 'piece', False),
    ('Boissons', 'Biere Primus 50cl', 'BP-50CL', 1200, 1500, 'piece', True),
    ('Boissons', 'Cafe Nescafe 200g', 'CF-NC-200', 5000, 7000, 'piece', False),
    # Alimentation
    ('Alimentation', 'Riz Thai 5kg', 'RZ-TH-5K', 8000, 10000, 'kg', True),
    ('Alimentation', 'Sucre 1kg', 'SC-1KG', 1800, 2200, 'kg', True),
    ('Alimentation', 'Huile Palme 1L', 'HP-1L', 3500, 4500, 'liter', True),
    ('Alimentation', 'Farine Ble 1kg', 'FB-1KG', 1500, 2000, 'kg', False),
    ('Alimentation', 'Sel 1kg', 'SL-1KG', 500, 800, 'kg', False),
    ('Alimentation', 'Haricots Rouges 1kg', 'HR-1KG', 2500, 3200, 'kg', True),
    # Hygiene
    ('Hygiene', 'Savon Lux 175g', 'SV-LX-175', 1200, 1600, 'piece', True),
    ('Hygiene', 'Dentifrice Colgate 100ml', 'DP-CG-100', 2000, 2800, 'piece', True),
    ('Hygiene', 'Papier Toilette x4', 'PT-X4', 2500, 3500, 'piece', True),
    ('Hygiene', 'Shampoing Head&Shoulders 200ml', 'SH-HS-200', 4000, 5500, 'piece', False),
    # Nettoyage
    ('Nettoyage', 'Eau de Javel 1L', 'EJ-1L', 1500, 2000, 'liter', True),
    ('Nettoyage', 'Detergent Omo 1kg', 'DT-OM-1K', 4500, 6000, 'kg', True),
    ('Nettoyage', 'Liquide Vaisselle 500ml', 'LV-500M', 2500, 3500, 'piece', False),
    # Confiserie
    ('Confiserie', 'Chocolat Dairy Milk 100g', 'CH-DM-100', 2500, 3500, 'piece', True),
    ('Confiserie', 'Biscuits Oreo', 'BS-OR', 1800, 2500, 'piece', False),
    ('Confiserie', 'Chips Lays 75g', 'CP-LY-75', 1500, 2200, 'piece', True),
    # Papeterie
    ('Papeterie', 'Cahier 100 pages', 'CH-100P', 800, 1200, 'piece', True),
    ('Papeterie', 'Stylo Bic Bleu x10', 'ST-BC-10', 2000, 3000, 'piece', True),
    # Electronique
    ('Electronique', 'Pile AA x4', 'PL-AA-4', 1500, 2200, 'piece', True),
    ('Electronique', 'Chargeur Telephone', 'CH-TEL', 5000, 8000, 'piece', False),
]

CATEGORY_DESCRIPTIONS = {
    'Boissons': 'Sodas, jus, eau, boissons energisantes',
    'Alimentation': 'Produits alimentaires de base',
    'Hygiene': "Produits d'hygiene personnelle",
    'Nettoyage': 'Produits de nettoyage menager',
    'Confiserie': 'Bonbons, chocolats, biscuits',
    'Papeterie': 'Fournitures de bureau et scolaires',
    'Electronique': 'Petits appareils electroniques',
}


class Command(BaseCommand):
    help = 'Seed a starter product catalog into existing enterprises (idempotent).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enterprise',
            dest='enterprise_code',
            default=None,
            help='Only seed the enterprise with this code (e.g. HEMA01).',
        )
        parser.add_argument(
            '--with-stock',
            action='store_true',
            help='Also create a Stock row (quantity 0) for each product at the main location.',
        )

    def handle(self, *args, **options):
        from apps.core.models import Enterprise

        enterprises = Enterprise.objects.all()
        if options['enterprise_code']:
            enterprises = enterprises.filter(code=options['enterprise_code'])

        if not enterprises.exists():
            self.stdout.write(self.style.ERROR(
                'No matching enterprise found. Create an enterprise first.'
            ))
            return

        for enterprise in enterprises:
            self._seed_enterprise(enterprise, with_stock=options['with_stock'])

    @transaction.atomic
    def _seed_enterprise(self, enterprise, with_stock=False):
        from apps.products.models import Category, Product

        self.stdout.write(self.style.SUCCESS(
            f'\nSeeding catalog for: {enterprise.name} ({enterprise.code})'
        ))

        # Categories
        categories = {}
        cats_created = 0
        for cat_name in CATEGORY_DESCRIPTIONS:
            category, created = Category.objects.get_or_create(
                enterprise=enterprise,
                name=cat_name,
                defaults={'description': CATEGORY_DESCRIPTIONS[cat_name], 'is_active': True},
            )
            categories[cat_name] = category
            cats_created += int(created)
        self.stdout.write(f'  Categories: {len(categories)} ensured ({cats_created} new)')

        # Products
        products_created = 0
        seeded_products = []
        for cat_name, name, sku, purchase, sale, unit, is_popular in CATALOG:
            category = categories.get(cat_name)
            if category is None:
                continue
            product, created = Product.objects.get_or_create(
                enterprise=enterprise,
                sku=sku,
                defaults={
                    'category': category,
                    'name': name,
                    'unit': unit,
                    'purchase_price': Decimal(str(purchase)),
                    'sale_price': Decimal(str(sale)),
                    'min_stock_threshold': 10,
                    'is_popular': is_popular,
                    'is_active': True,
                },
            )
            products_created += int(created)
            seeded_products.append(product)
        self.stdout.write(self.style.SUCCESS(
            f'  Products: {len(seeded_products)} ensured ({products_created} new)'
        ))

        if with_stock:
            self._ensure_stock(enterprise, seeded_products)

    def _ensure_stock(self, enterprise, products):
        from apps.locations.models import Location
        from apps.stock.models import Stock

        location = (
            Location.objects.filter(enterprise=enterprise, is_main_warehouse=True).first()
            or Location.objects.filter(enterprise=enterprise, is_active=True).first()
        )
        if location is None:
            self.stdout.write(self.style.WARNING(
                '  No location found; skipping stock rows.'
            ))
            return

        created = 0
        for product in products:
            _, was_created = Stock.objects.get_or_create(
                enterprise=enterprise,
                location=location,
                product=product,
                defaults={'quantity': Decimal('0')},
            )
            created += int(was_created)
        self.stdout.write(f'  Stock rows at {location.name}: {created} created')
