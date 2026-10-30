"""
Comprehensive seed data for Stock Control & POS system.

Business Scenario:
- One enterprise (Commerce General)
- Main warehouse (Depot Principal) where merchandise is received
- 3 Boutiques that receive stock via transfers from the warehouse
- Each boutique has its own cashiers and manages sales independently
- Owner oversees everything, managers run boutiques
"""

import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate comprehensive seed data for testing all dashboards'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('   STOCK CONTROL & POS - COMPREHENSIVE DATA SEEDING'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        if options['clear']:
            self.clear_data()

        with transaction.atomic():
            enterprise = self.create_enterprise()
            locations = self.create_locations(enterprise)
            users = self.create_users(enterprise, locations)
            categories = self.create_categories(enterprise)
            products = self.create_products(enterprise, categories)
            self.create_initial_stock(enterprise, locations, products, users)
            self.create_transfers(enterprise, locations, products, users)
            customers = self.create_customers(enterprise)
            self.create_sales(enterprise, locations, products, customers, users)
            self.create_expenses(enterprise, locations, users)
            self.create_daily_summaries(enterprise, locations)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('   SEEDING COMPLETED SUCCESSFULLY!'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        self.print_login_credentials(users)

    def clear_data(self):
        """Clear existing data"""
        self.stdout.write('Clearing existing data...')
        from apps.pos.models import Sale, SaleItem
        from apps.stock.models import Stock, StockMovement
        from apps.transfers.models import Transfer, TransferItem
        from apps.customers.models import Customer, CustomerCredit, CreditPayment
        from apps.products.models import Product, Category, ProductPackaging
        from apps.accounting.models import Expense, ExpenseCategory, DailySummary
        from apps.locations.models import Location
        from apps.core.models import Enterprise

        # Delete in order of dependencies
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        CreditPayment.objects.all().delete()
        CustomerCredit.objects.all().delete()
        TransferItem.objects.all().delete()
        Transfer.objects.all().delete()
        StockMovement.objects.all().delete()
        Stock.objects.all().delete()
        DailySummary.objects.all().delete()
        Expense.objects.all().delete()
        Customer.objects.all().delete()
        ProductPackaging.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('  Data cleared!'))

    def create_enterprise(self):
        """Create or get the main enterprise"""
        self.stdout.write('\n[1/10] Creating Enterprise...')
        from apps.core.models import Enterprise

        enterprise, created = Enterprise.objects.get_or_create(
            code='CGM-001',
            defaults={
                'name': 'Commerce General Multi-Boutiques',
                'address': '123 Avenue Principale, Bujumbura',
                'phone': '+257 79 123 456',
                'email': 'contact@cgm.bi',
                'currency': 'BIF',
                'is_active': True,
            }
        )
        action = 'Created' if created else 'Found existing'
        self.stdout.write(self.style.SUCCESS(f'  {action} enterprise: {enterprise.name}'))
        return enterprise

    def create_locations(self, enterprise):
        """Create warehouse and boutiques"""
        self.stdout.write('\n[2/10] Creating Locations...')
        from apps.locations.models import Location

        locations_data = [
            {
                'name': 'Depot Central',
                'code': 'DEPOT-MAIN',
                'location_type': 'warehouse',
                'address': 'Zone Industrielle, Bujumbura',
                'phone': '+257 79 111 111',
                'is_main_warehouse': True,
            },
            {
                'name': 'Boutique Centre-Ville',
                'code': 'BTQ-CENTRE',
                'location_type': 'boutique',
                'address': 'Rue du Commerce 45, Centre-Ville',
                'phone': '+257 79 222 222',
                'is_main_warehouse': False,
            },
            {
                'name': 'Boutique Quartier Nord',
                'code': 'BTQ-NORD',
                'location_type': 'boutique',
                'address': 'Avenue de la Paix 78, Ngagara',
                'phone': '+257 79 333 333',
                'is_main_warehouse': False,
            },
            {
                'name': 'Boutique Quartier Sud',
                'code': 'BTQ-SUD',
                'location_type': 'boutique',
                'address': 'Boulevard du Sud 12, Musaga',
                'phone': '+257 79 444 444',
                'is_main_warehouse': False,
            },
        ]

        locations = {}
        for loc_data in locations_data:
            location, created = Location.objects.get_or_create(
                enterprise=enterprise,
                code=loc_data['code'],
                defaults=loc_data
            )
            locations[loc_data['code']] = location
            action = 'Created' if created else 'Found'
            self.stdout.write(f'  {action}: {location.name}')

        return locations

    def create_users(self, enterprise, locations):
        """Create users with different roles"""
        self.stdout.write('\n[3/10] Creating Users...')

        users_data = [
            # Owner (main admin)
            {
                'username': 'patron',
                'email': 'patron@cgm.bi',
                'password': 'patron123',
                'first_name': 'Jean-Pierre',
                'last_name': 'Ndayisaba',
                'role': 'owner',
                'location_code': None,
            },
            # Warehouse Manager
            {
                'username': 'depot_manager',
                'email': 'depot@cgm.bi',
                'password': 'depot123',
                'first_name': 'Emmanuel',
                'last_name': 'Niyonzima',
                'role': 'warehouse_manager',
                'location_code': 'DEPOT-MAIN',
            },
            # Boutique Managers
            {
                'username': 'manager_centre',
                'email': 'centre@cgm.bi',
                'password': 'centre123',
                'first_name': 'Marie',
                'last_name': 'Niyonsaba',
                'role': 'boutique_manager',
                'location_code': 'BTQ-CENTRE',
            },
            {
                'username': 'manager_nord',
                'email': 'nord@cgm.bi',
                'password': 'nord123',
                'first_name': 'Patrick',
                'last_name': 'Habimana',
                'role': 'boutique_manager',
                'location_code': 'BTQ-NORD',
            },
            {
                'username': 'manager_sud',
                'email': 'sud@cgm.bi',
                'password': 'sud123',
                'first_name': 'Diane',
                'last_name': 'Irakoze',
                'role': 'boutique_manager',
                'location_code': 'BTQ-SUD',
            },
            # Cashiers for each boutique
            {
                'username': 'caisse_centre1',
                'email': 'caisse_centre1@cgm.bi',
                'password': 'caisse123',
                'first_name': 'Alice',
                'last_name': 'Bukuru',
                'role': 'cashier',
                'location_code': 'BTQ-CENTRE',
            },
            {
                'username': 'caisse_centre2',
                'email': 'caisse_centre2@cgm.bi',
                'password': 'caisse123',
                'first_name': 'Bob',
                'last_name': 'Manirambona',
                'role': 'cashier',
                'location_code': 'BTQ-CENTRE',
            },
            {
                'username': 'caisse_nord1',
                'email': 'caisse_nord1@cgm.bi',
                'password': 'caisse123',
                'first_name': 'Claire',
                'last_name': 'Nduwimana',
                'role': 'cashier',
                'location_code': 'BTQ-NORD',
            },
            {
                'username': 'caisse_sud1',
                'email': 'caisse_sud1@cgm.bi',
                'password': 'caisse123',
                'first_name': 'David',
                'last_name': 'Nshimirimana',
                'role': 'cashier',
                'location_code': 'BTQ-SUD',
            },
            # Stock Manager
            {
                'username': 'stock_manager',
                'email': 'stock@cgm.bi',
                'password': 'stock123',
                'first_name': 'Eric',
                'last_name': 'Bizimana',
                'role': 'stock_manager',
                'location_code': 'DEPOT-MAIN',
            },
            # Accountant
            {
                'username': 'comptable',
                'email': 'comptable@cgm.bi',
                'password': 'comptable123',
                'first_name': 'Florence',
                'last_name': 'Niyonkuru',
                'role': 'accountant',
                'location_code': None,
            },
        ]

        users = {}
        for user_data in users_data:
            location = locations.get(user_data['location_code']) if user_data['location_code'] else None
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': user_data['role'],
                    'enterprise': enterprise,
                    'location': location,
                    'is_active': True,
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
            users[user_data['username']] = user
            action = 'Created' if created else 'Found'
            self.stdout.write(f'  {action}: {user.get_full_name()} ({user.role})')

        return users

    def create_categories(self, enterprise):
        """Create product categories"""
        self.stdout.write('\n[4/10] Creating Categories...')
        from apps.products.models import Category

        categories_data = [
            ('Boissons', 'Sodas, jus, eau, boissons energisantes'),
            ('Alimentation', 'Produits alimentaires de base'),
            ('Hygiene', 'Produits d\'hygiene personnelle'),
            ('Nettoyage', 'Produits de nettoyage menager'),
            ('Cosmetiques', 'Produits de beaute et soins'),
            ('Electronique', 'Petits appareils electroniques'),
            ('Papeterie', 'Fournitures de bureau et scolaires'),
            ('Confiserie', 'Bonbons, chocolats, biscuits'),
            ('Laiterie', 'Lait, yaourt, fromage'),
            ('Conserves', 'Boites de conserve et bocaux'),
        ]

        categories = {}
        for name, description in categories_data:
            category, created = Category.objects.get_or_create(
                enterprise=enterprise,
                name=name,
                defaults={'description': description, 'is_active': True}
            )
            categories[name] = category
            action = 'Created' if created else 'Found'
            self.stdout.write(f'  {action}: {name}')

        return categories

    def create_products(self, enterprise, categories):
        """Create products with realistic prices"""
        self.stdout.write('\n[5/10] Creating Products (80 products)...')
        from apps.products.models import Product

        products_data = [
            # Boissons (15 products)
            ('Boissons', 'Coca-Cola 50cl', 'CC-50CL', 800, 1000, 'piece', True),
            ('Boissons', 'Coca-Cola 1L', 'CC-1L', 1400, 1800, 'piece', True),
            ('Boissons', 'Fanta Orange 50cl', 'FO-50CL', 800, 1000, 'piece', True),
            ('Boissons', 'Sprite 50cl', 'SP-50CL', 800, 1000, 'piece', False),
            ('Boissons', 'Eau Minerale 1.5L', 'EM-1.5L', 600, 800, 'piece', True),
            ('Boissons', 'Eau Minerale 50cl', 'EM-50CL', 300, 500, 'piece', False),
            ('Boissons', 'Jus Rani Mangue 1L', 'JR-MG-1L', 1800, 2500, 'piece', False),
            ('Boissons', 'Jus Rani Orange 1L', 'JR-OR-1L', 1800, 2500, 'piece', False),
            ('Boissons', 'Red Bull 25cl', 'RB-25CL', 2000, 2800, 'piece', False),
            ('Boissons', 'Monster Energy 50cl', 'ME-50CL', 2200, 3000, 'piece', False),
            ('Boissons', 'Biere Primus 50cl', 'BP-50CL', 1200, 1500, 'piece', True),
            ('Boissons', 'Biere Amstel 50cl', 'BA-50CL', 1400, 1800, 'piece', False),
            ('Boissons', 'Vin Rouge 75cl', 'VR-75CL', 8000, 12000, 'piece', False),
            ('Boissons', 'Whisky JB 75cl', 'WH-JB-75', 25000, 35000, 'piece', False),
            ('Boissons', 'Cafe Nescafe 200g', 'CF-NC-200', 5000, 7000, 'piece', False),

            # Alimentation (15 products)
            ('Alimentation', 'Riz Thai 5kg', 'RZ-TH-5K', 8000, 10000, 'kg', True),
            ('Alimentation', 'Riz Thai 25kg', 'RZ-TH-25K', 38000, 45000, 'kg', False),
            ('Alimentation', 'Sucre 1kg', 'SC-1KG', 1800, 2200, 'kg', True),
            ('Alimentation', 'Sucre 50kg', 'SC-50KG', 85000, 95000, 'kg', False),
            ('Alimentation', 'Huile Palme 1L', 'HP-1L', 3500, 4500, 'liter', True),
            ('Alimentation', 'Huile Palme 5L', 'HP-5L', 16000, 20000, 'liter', False),
            ('Alimentation', 'Farine Ble 1kg', 'FB-1KG', 1500, 2000, 'kg', False),
            ('Alimentation', 'Farine Ble 25kg', 'FB-25KG', 35000, 42000, 'kg', False),
            ('Alimentation', 'Sel 1kg', 'SL-1KG', 500, 800, 'kg', False),
            ('Alimentation', 'Pates Spaghetti 500g', 'PS-500G', 1200, 1600, 'piece', False),
            ('Alimentation', 'Haricots Rouges 1kg', 'HR-1KG', 2500, 3200, 'kg', True),
            ('Alimentation', 'Mais 1kg', 'MS-1KG', 1200, 1600, 'kg', False),
            ('Alimentation', 'Lentilles 1kg', 'LT-1KG', 3000, 3800, 'kg', False),
            ('Alimentation', 'Oignons 1kg', 'OG-1KG', 2000, 2800, 'kg', False),
            ('Alimentation', 'Tomates 1kg', 'TM-1KG', 1500, 2200, 'kg', False),

            # Hygiene (10 products)
            ('Hygiene', 'Savon Lux 175g', 'SV-LX-175', 1200, 1600, 'piece', True),
            ('Hygiene', 'Savon Palmolive 175g', 'SV-PM-175', 1000, 1400, 'piece', False),
            ('Hygiene', 'Dentifrice Colgate 100ml', 'DP-CG-100', 2000, 2800, 'piece', True),
            ('Hygiene', 'Brosse a Dents', 'BD-STD', 800, 1200, 'piece', False),
            ('Hygiene', 'Shampoing Head&Shoulders 200ml', 'SH-HS-200', 4000, 5500, 'piece', False),
            ('Hygiene', 'Deodorant Nivea 150ml', 'DO-NV-150', 3500, 4800, 'piece', False),
            ('Hygiene', 'Papier Toilette x4', 'PT-X4', 2500, 3500, 'piece', True),
            ('Hygiene', 'Serviettes Always x10', 'SR-AW-10', 2000, 2800, 'piece', False),
            ('Hygiene', 'Coton Tiges x100', 'CT-X100', 1000, 1500, 'piece', False),
            ('Hygiene', 'Rasoir Gillette x5', 'RG-X5', 3000, 4200, 'piece', False),

            # Nettoyage (10 products)
            ('Nettoyage', 'Eau de Javel 1L', 'EJ-1L', 1500, 2000, 'liter', True),
            ('Nettoyage', 'Detergent Omo 1kg', 'DT-OM-1K', 4500, 6000, 'kg', True),
            ('Nettoyage', 'Savon en Poudre 500g', 'SP-500G', 2000, 2800, 'piece', False),
            ('Nettoyage', 'Liquide Vaisselle 500ml', 'LV-500M', 2500, 3500, 'piece', False),
            ('Nettoyage', 'Balai', 'BL-STD', 3000, 4500, 'piece', False),
            ('Nettoyage', 'Serpilliere', 'SR-STD', 2000, 3000, 'piece', False),
            ('Nettoyage', 'Seau 10L', 'SE-10L', 2500, 4000, 'piece', False),
            ('Nettoyage', 'Desinfectant 500ml', 'DS-500M', 3500, 5000, 'piece', False),
            ('Nettoyage', 'Insecticide Raid 300ml', 'IS-RD-300', 4000, 5500, 'piece', False),
            ('Nettoyage', 'Eponge x3', 'EP-X3', 800, 1200, 'piece', False),

            # Cosmetiques (8 products)
            ('Cosmetiques', 'Creme Nivea 200ml', 'CR-NV-200', 4500, 6500, 'piece', False),
            ('Cosmetiques', 'Vaseline 250ml', 'VS-250M', 2500, 3500, 'piece', True),
            ('Cosmetiques', 'Huile Corporelle 200ml', 'HC-200M', 3000, 4200, 'piece', False),
            ('Cosmetiques', 'Parfum 50ml', 'PF-50M', 8000, 12000, 'piece', False),
            ('Cosmetiques', 'Vernis a Ongles', 'VN-STD', 1500, 2500, 'piece', False),
            ('Cosmetiques', 'Rouge a Levres', 'RL-STD', 2000, 3500, 'piece', False),
            ('Cosmetiques', 'Mascara', 'MS-STD', 3000, 5000, 'piece', False),
            ('Cosmetiques', 'Fond de Teint', 'FT-STD', 5000, 8000, 'piece', False),

            # Electronique (6 products)
            ('Electronique', 'Pile AA x4', 'PL-AA-4', 1500, 2200, 'piece', True),
            ('Electronique', 'Pile AAA x4', 'PL-AAA-4', 1500, 2200, 'piece', False),
            ('Electronique', 'Chargeur Telephone', 'CH-TEL', 5000, 8000, 'piece', False),
            ('Electronique', 'Ecouteurs', 'EC-STD', 3000, 5000, 'piece', False),
            ('Electronique', 'Cable USB', 'CB-USB', 2500, 4000, 'piece', False),
            ('Electronique', 'Lampe Torche LED', 'LT-LED', 4000, 6500, 'piece', False),

            # Papeterie (8 products)
            ('Papeterie', 'Cahier 100 pages', 'CH-100P', 800, 1200, 'piece', True),
            ('Papeterie', 'Cahier 200 pages', 'CH-200P', 1500, 2200, 'piece', False),
            ('Papeterie', 'Stylo Bic Bleu x10', 'ST-BC-10', 2000, 3000, 'piece', True),
            ('Papeterie', 'Crayon HB x12', 'CR-HB-12', 1500, 2500, 'piece', False),
            ('Papeterie', 'Gomme', 'GM-STD', 300, 500, 'piece', False),
            ('Papeterie', 'Taille-Crayon', 'TC-STD', 400, 700, 'piece', False),
            ('Papeterie', 'Regle 30cm', 'RG-30CM', 500, 800, 'piece', False),
            ('Papeterie', 'Scotch', 'SC-STD', 800, 1200, 'piece', False),

            # Confiserie (8 products)
            ('Confiserie', 'Chocolat Dairy Milk 100g', 'CH-DM-100', 2500, 3500, 'piece', True),
            ('Confiserie', 'Bonbons Mentos', 'BN-MT', 500, 800, 'piece', True),
            ('Confiserie', 'Chewing-gum Orbit', 'CG-OR', 600, 1000, 'piece', False),
            ('Confiserie', 'Biscuits Oreo', 'BS-OR', 1800, 2500, 'piece', False),
            ('Confiserie', 'Chips Lays 75g', 'CP-LY-75', 1500, 2200, 'piece', True),
            ('Confiserie', 'Cacahuetes 200g', 'CC-200G', 1200, 1800, 'piece', False),
            ('Confiserie', 'Pop-corn 100g', 'PC-100G', 1000, 1500, 'piece', False),
            ('Confiserie', 'Sucette Chupa Chups', 'SU-CC', 200, 400, 'piece', False),
        ]

        products = []
        for cat_name, name, sku, purchase, sale, unit, is_popular in products_data:
            category = categories.get(cat_name)
            if not category:
                continue

            barcode = f'695{random.randint(1000000000, 9999999999)}'
            product, created = Product.objects.get_or_create(
                enterprise=enterprise,
                sku=sku,
                defaults={
                    'category': category,
                    'name': name,
                    'barcode': barcode,
                    'unit': unit,
                    'purchase_price': Decimal(str(purchase)),
                    'sale_price': Decimal(str(sale)),
                    'min_stock_threshold': random.randint(5, 20),
                    'is_popular': is_popular,
                    'is_active': True,
                }
            )
            products.append(product)

        self.stdout.write(self.style.SUCCESS(f'  Created/Found {len(products)} products'))
        return products

    def create_initial_stock(self, enterprise, locations, products, users):
        """Create initial stock in warehouse"""
        self.stdout.write('\n[6/10] Creating Initial Stock in Warehouse...')
        from apps.stock.models import Stock, StockMovement

        warehouse = locations['DEPOT-MAIN']
        stock_user = users.get('stock_manager') or users.get('patron')

        for product in products:
            # Random initial quantity between 50 and 500
            quantity = Decimal(str(random.randint(50, 500)))

            stock, created = Stock.objects.get_or_create(
                enterprise=enterprise,
                location=warehouse,
                product=product,
                defaults={'quantity': quantity}
            )

            if created:
                # Create stock entry movement
                StockMovement.objects.create(
                    enterprise=enterprise,
                    location=warehouse,
                    product=product,
                    user=stock_user,
                    movement_type='entry',
                    reason='initial_stock',
                    quantity=quantity,
                    unit_cost=product.purchase_price,
                    notes='Stock initial du depot'
                )

        self.stdout.write(self.style.SUCCESS(f'  Created stock for {len(products)} products in warehouse'))

    def create_transfers(self, enterprise, locations, products, users):
        """Create transfers from warehouse to boutiques"""
        self.stdout.write('\n[7/10] Creating Transfers to Boutiques...')
        from apps.transfers.models import Transfer, TransferItem
        from apps.stock.models import Stock, StockMovement

        warehouse = locations['DEPOT-MAIN']
        boutiques = [locations['BTQ-CENTRE'], locations['BTQ-NORD'], locations['BTQ-SUD']]
        depot_manager = users.get('depot_manager') or users.get('patron')

        transfer_count = 0

        # Create transfers over the last 30 days
        for days_ago in range(30, 0, -3):  # Every 3 days
            transfer_date = timezone.now() - timedelta(days=days_ago)

            for boutique in boutiques:
                # Create transfer
                transfer = Transfer.objects.create(
                    enterprise=enterprise,
                    source_location=warehouse,
                    destination_location=boutique,
                    status='received',
                    notes=f'Approvisionnement {boutique.name}',
                    created_by=depot_manager,
                    sent_by=depot_manager,
                    received_by=users.get(f'manager_{boutique.code.split("-")[1].lower()}') or depot_manager,
                    sent_at=transfer_date,
                    received_at=transfer_date + timedelta(hours=2),
                )
                transfer.created_at = transfer_date
                transfer.save()

                # Add random products to transfer
                selected_products = random.sample(products, min(len(products), random.randint(10, 20)))

                for product in selected_products:
                    quantity = Decimal(str(random.randint(10, 50)))

                    TransferItem.objects.create(
                        transfer=transfer,
                        product=product,
                        quantity=quantity,
                        received_quantity=quantity,
                        unit_cost=product.purchase_price,
                    )

                    # Update boutique stock
                    stock, created = Stock.objects.get_or_create(
                        enterprise=enterprise,
                        location=boutique,
                        product=product,
                        defaults={'quantity': Decimal('0')}
                    )
                    stock.quantity += quantity
                    stock.save()

                    # Create stock movement for boutique
                    StockMovement.objects.create(
                        enterprise=enterprise,
                        location=boutique,
                        product=product,
                        user=depot_manager,
                        movement_type='entry',
                        reason='transfer_in',
                        quantity=quantity,
                        unit_cost=product.purchase_price,
                        reference=transfer.reference,
                        notes=f'Reception transfert {transfer.reference}'
                    )

                transfer_count += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {transfer_count} transfers'))

    def create_customers(self, enterprise):
        """Create customers"""
        self.stdout.write('\n[8/10] Creating Customers (120 customers)...')
        from apps.customers.models import Customer

        first_names = [
            'Jean', 'Marie', 'Pierre', 'Anne', 'Paul', 'Claire', 'Jacques', 'Sophie',
            'Emmanuel', 'Diane', 'Patrick', 'Florence', 'Eric', 'Alice', 'David', 'Rachel',
            'Michel', 'Christine', 'Robert', 'Jeanne', 'Francis', 'Beatrice', 'Joseph', 'Agnes',
            'Bernard', 'Monique', 'Claude', 'Therese', 'Philippe', 'Pascaline'
        ]

        last_names = [
            'Ndayisaba', 'Niyonzima', 'Habimana', 'Irakoze', 'Bukuru', 'Manirambona',
            'Nduwimana', 'Nshimirimana', 'Bizimana', 'Niyonkuru', 'Nsengiyumva', 'Hakizimana',
            'Niyongabo', 'Nkurunziza', 'Havyarimana', 'Rugamba', 'Ntakirutimana', 'Ndikumana',
            'Manirakiza', 'Niyibigira', 'Ndayizeye', 'Sindayigaya', 'Nzeyimana', 'Bigirimana',
            'Niyokwizera', 'Hatungimana', 'Niyomugabo', 'Mushimiyimana', 'Niyigena', 'Niyomwungeri'
        ]

        customers = []
        for i in range(120):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            phone = f'+257 7{random.randint(1, 9)} {random.randint(100, 999)} {random.randint(100, 999)}'

            customer, created = Customer.objects.get_or_create(
                enterprise=enterprise,
                phone=phone,
                defaults={
                    'name': f'{first_name} {last_name}',
                    'email': f'{first_name.lower()}.{last_name.lower()}{i}@email.bi' if random.random() > 0.7 else None,
                    'address': f'Quartier {random.choice(["Rohero", "Ngagara", "Musaga", "Buyenzi", "Bwiza", "Kinama"])}, Bujumbura' if random.random() > 0.5 else None,
                    'credit_limit': Decimal(str(random.choice([0, 50000, 100000, 200000, 500000]))),
                    'is_active': True,
                }
            )
            customers.append(customer)

        self.stdout.write(self.style.SUCCESS(f'  Created/Found {len(customers)} customers'))
        return customers

    def create_sales(self, enterprise, locations, products, customers, users):
        """Create sales transactions over the past 60 days"""
        self.stdout.write('\n[9/10] Creating Sales (100+ per boutique)...')
        from apps.pos.models import Sale, SaleItem
        from apps.stock.models import Stock, StockMovement

        boutiques = [locations['BTQ-CENTRE'], locations['BTQ-NORD'], locations['BTQ-SUD']]
        payment_methods = ['cash', 'cash', 'cash', 'mobile_money', 'mobile_money', 'card']

        # Map boutiques to their cashiers
        boutique_cashiers = {
            'BTQ-CENTRE': [users.get('caisse_centre1'), users.get('caisse_centre2'), users.get('manager_centre')],
            'BTQ-NORD': [users.get('caisse_nord1'), users.get('manager_nord')],
            'BTQ-SUD': [users.get('caisse_sud1'), users.get('manager_sud')],
        }

        total_sales = 0

        # Generate sales for the past 60 days
        for days_ago in range(60, -1, -1):
            sale_date = timezone.now() - timedelta(days=days_ago)

            # More sales on weekends and recent days
            is_weekend = sale_date.weekday() >= 5
            base_sales = 8 if is_weekend else 5
            if days_ago < 7:
                base_sales += 3  # More recent sales

            for boutique in boutiques:
                # Random number of sales per day per boutique
                num_sales = random.randint(base_sales - 2, base_sales + 5)

                cashiers = [c for c in boutique_cashiers.get(boutique.code, []) if c]
                if not cashiers:
                    cashiers = [users.get('patron')]

                for _ in range(num_sales):
                    # Random time during business hours (7 AM to 9 PM)
                    hour = random.randint(7, 21)
                    minute = random.randint(0, 59)
                    sale_datetime = sale_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                    # Random customer (70% have customer, 30% anonymous)
                    customer = random.choice(customers) if random.random() > 0.3 else None
                    cashier = random.choice(cashiers)
                    payment_method = random.choice(payment_methods)

                    # Create sale
                    sale = Sale(
                        enterprise=enterprise,
                        location=boutique,
                        sale_number=Sale.generate_sale_number(),
                        customer=customer,
                        user=cashier,
                        payment_method=payment_method,
                        status='completed',
                    )

                    # Add 1-6 items to the sale
                    num_items = random.randint(1, 6)
                    selected_products = random.sample(products, min(len(products), num_items))

                    subtotal = Decimal('0')
                    sale_items = []

                    for product in selected_products:
                        quantity = Decimal(str(random.randint(1, 5)))
                        unit_price = product.sale_price
                        line_total = quantity * unit_price

                        sale_items.append({
                            'product': product,
                            'product_name': product.name,
                            'quantity': quantity,
                            'unit_price': unit_price,
                            'purchase_price': product.purchase_price,
                            'total_price': line_total,
                        })

                        subtotal += line_total

                    # Calculate totals
                    discount_percent = Decimal(str(random.choice([0, 0, 0, 5, 10])))
                    discount_amount = (subtotal * discount_percent / 100).quantize(Decimal('0.01'))
                    total_amount = subtotal - discount_amount

                    sale.subtotal = subtotal
                    sale.discount_percent = discount_percent
                    sale.discount_amount = discount_amount
                    sale.total_amount = total_amount
                    sale.amount_paid = total_amount if payment_method != 'credit' else Decimal('0')
                    sale.change_amount = Decimal('0')

                    sale.save()

                    # Override created_at
                    Sale.objects.filter(pk=sale.pk).update(created_at=sale_datetime)

                    # Create sale items
                    for item_data in sale_items:
                        SaleItem.objects.create(sale=sale, **item_data)

                        # Update stock (reduce boutique stock)
                        try:
                            stock = Stock.objects.get(
                                enterprise=enterprise,
                                location=boutique,
                                product=item_data['product']
                            )
                            stock.quantity -= item_data['quantity']
                            if stock.quantity < 0:
                                stock.quantity = Decimal('0')
                            stock.save()
                        except Stock.DoesNotExist:
                            pass

                    # Update customer stats
                    if customer:
                        customer.total_purchases += total_amount
                        customer.purchase_count += 1
                        customer.save()

                    total_sales += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {total_sales} sales across all boutiques'))

    def create_expenses(self, enterprise, locations, users):
        """Create expenses"""
        self.stdout.write('\n[10/10] Creating Expenses...')
        from apps.accounting.models import Expense, ExpenseCategory

        # Create expense categories if they don't exist
        categories_data = [
            ('Loyer', 'Loyer mensuel des locaux'),
            ('Electricite', 'Factures d\'electricite'),
            ('Eau', 'Factures d\'eau'),
            ('Salaires', 'Salaires des employes'),
            ('Transport', 'Frais de transport et livraison'),
            ('Maintenance', 'Entretien des equipements'),
            ('Fournitures', 'Fournitures de bureau'),
            ('Marketing', 'Publicite et promotion'),
            ('Divers', 'Autres depenses'),
        ]

        expense_categories = {}
        for name, description in categories_data:
            cat, _ = ExpenseCategory.objects.get_or_create(
                enterprise=enterprise,
                name=name,
                defaults={'description': description}
            )
            expense_categories[name] = cat

        boutiques = [locations['BTQ-CENTRE'], locations['BTQ-NORD'], locations['BTQ-SUD']]
        admin_user = users.get('patron')

        expense_count = 0

        # Create monthly recurring expenses
        for month_offset in range(2, -1, -1):
            expense_date = timezone.now() - timedelta(days=month_offset * 30)

            for boutique in boutiques:
                # Rent
                Expense.objects.create(
                    enterprise=enterprise,
                    location=boutique,
                    expense_category=expense_categories['Loyer'],
                    description=f'Loyer {boutique.name} - {expense_date.strftime("%B %Y")}',
                    amount=Decimal(str(random.randint(300000, 500000))),
                    expense_date=expense_date.date(),
                    payment_method='cash',
                    user=admin_user,
                )
                expense_count += 1

                # Electricity
                Expense.objects.create(
                    enterprise=enterprise,
                    location=boutique,
                    expense_category=expense_categories['Electricite'],
                    description=f'Electricite {boutique.name} - {expense_date.strftime("%B %Y")}',
                    amount=Decimal(str(random.randint(50000, 150000))),
                    expense_date=expense_date.date(),
                    payment_method='mobile_money',
                    user=admin_user,
                )
                expense_count += 1

        # Random daily expenses over past 30 days
        for days_ago in range(30, 0, -1):
            expense_date = timezone.now() - timedelta(days=days_ago)

            # 50% chance of expense each day
            if random.random() > 0.5:
                boutique = random.choice(boutiques)
                category = random.choice(list(expense_categories.values()))

                Expense.objects.create(
                    enterprise=enterprise,
                    location=boutique,
                    expense_category=category,
                    description=f'{category.name} - {boutique.name}',
                    amount=Decimal(str(random.randint(5000, 50000))),
                    expense_date=expense_date.date(),
                    payment_method=random.choice(['cash', 'mobile_money']),
                    user=admin_user,
                )
                expense_count += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {expense_count} expenses'))

    def create_daily_summaries(self, enterprise, locations):
        """Generate daily summaries for past 30 days"""
        self.stdout.write('\nGenerating Daily Summaries...')
        from apps.accounting.models import DailySummary
        from apps.pos.models import Sale
        from apps.accounting.models import Expense
        from django.db.models import Sum, Count

        boutiques = [locations['BTQ-CENTRE'], locations['BTQ-NORD'], locations['BTQ-SUD']]

        for days_ago in range(30, 0, -1):
            summary_date = (timezone.now() - timedelta(days=days_ago)).date()

            for boutique in boutiques:
                # Calculate daily stats
                daily_sales = Sale.objects.filter(
                    enterprise=enterprise,
                    location=boutique,
                    created_at__date=summary_date,
                    status='completed'
                ).aggregate(
                    total=Sum('total_amount'),
                    count=Count('id')
                )

                daily_expenses = Expense.objects.filter(
                    enterprise=enterprise,
                    location=boutique,
                    created_at__date=summary_date
                ).aggregate(total=Sum('amount'))

                total_sales = daily_sales['total'] or Decimal('0')
                sales_count = daily_sales['count'] or 0
                total_expenses = daily_expenses['total'] or Decimal('0')

                if sales_count > 0 or total_expenses > 0:
                    DailySummary.objects.update_or_create(
                        enterprise=enterprise,
                        location=boutique,
                        summary_date=summary_date,
                        defaults={
                            'total_sales': total_sales,
                            'number_of_sales': sales_count,
                            'total_expenses': total_expenses,
                        }
                    )

        self.stdout.write(self.style.SUCCESS('  Daily summaries generated'))

    def print_login_credentials(self, users):
        """Print login credentials for testing"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING('   LOGIN CREDENTIALS FOR TESTING'))
        self.stdout.write('=' * 60)

        credentials = [
            ('patron', 'patron123', 'Owner - Full access'),
            ('depot_manager', 'depot123', 'Warehouse Manager'),
            ('manager_centre', 'centre123', 'Manager - Boutique Centre'),
            ('manager_nord', 'nord123', 'Manager - Boutique Nord'),
            ('manager_sud', 'sud123', 'Manager - Boutique Sud'),
            ('caisse_centre1', 'caisse123', 'Cashier - Boutique Centre'),
            ('caisse_nord1', 'caisse123', 'Cashier - Boutique Nord'),
            ('caisse_sud1', 'caisse123', 'Cashier - Boutique Sud'),
            ('stock_manager', 'stock123', 'Stock Manager'),
            ('comptable', 'comptable123', 'Accountant'),
        ]

        self.stdout.write('')
        self.stdout.write(f'{"Username":<20} {"Password":<15} {"Role"}')
        self.stdout.write('-' * 60)
        for username, password, role in credentials:
            self.stdout.write(f'{username:<20} {password:<15} {role}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Use these credentials to log in and test the dashboards!'))
        self.stdout.write('=' * 60 + '\n')
