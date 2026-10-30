"""
Build a realistic multi-location test scenario for an enterprise:

  - Stock the MAIN DEPOT with `--units` of every active product (default 500),
    via real stock-entry movements.
  - Ensure `--boutiques` active boutiques exist (default 3).
  - DISTRIBUTE `--per-boutique` of every product to each boutique using REAL
    transfers (created → sent → received), so the whole transfer + stock flow
    is exercised end to end.

Idempotent: re-running won't double-stock (initial depot entry is created once
per product; scenario transfers are created once per boutique).

Usage:
    python manage.py seed_scenario
    python manage.py seed_scenario --units 500 --per-boutique 50 --boutiques 3
    python manage.py seed_scenario --enterprise HEMA01
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed a multi-location scenario: stock the depot and distribute to boutiques.'

    # Rôle : déclare --enterprise, --units, --per-boutique, --boutiques, --reset et --demo-cases.
    # Liens : appelée par Django au lancement de la commande ; valeurs lues par Command.handle.
    def add_arguments(self, parser):
        parser.add_argument('--enterprise', dest='enterprise_code', default=None,
                            help='Enterprise code (default: the one with a main warehouse).')
        parser.add_argument('--units', type=int, default=500,
                            help='Initial depot stock per product (default 500).')
        parser.add_argument('--per-boutique', dest='per_boutique', type=int, default=50,
                            help='Quantity of each product sent to each boutique (default 50).')
        parser.add_argument('--boutiques', type=int, default=3,
                            help='Number of boutiques to ensure/distribute to (default 3).')
        parser.add_argument('--reset', action='store_true',
                            help='Wipe this enterprise inventory (stock, movements, transfers) first for a clean rebuild.')
        parser.add_argument('--demo-cases', dest='demo_cases', action='store_true',
                            help='Create example Stock Faible (low) and Rupture (out-of-stock) cases at a boutique.')

    # Rôle : choisit l'entreprise (option, sinon celle du dépôt principal, sinon la première) et lance le scénario.
    # Liens : python manage.py seed_scenario et tests/test_multilocation_inventory.py ; appelle Command._run.
    def handle(self, *args, **opts):
        from apps.core.models import Enterprise
        from apps.locations.models import Location

        # Resolve enterprise.
        if opts['enterprise_code']:
            enterprise = Enterprise.objects.filter(code=opts['enterprise_code']).first()
        else:
            main = Location.objects.filter(is_main_warehouse=True).first()
            enterprise = main.enterprise if main else Enterprise.objects.first()

        if not enterprise:
            self.stdout.write(self.style.ERROR('No enterprise found.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\nScenario for: {enterprise.name} ({enterprise.code})'
        ))
        self._run(enterprise, opts['units'], opts['per_boutique'], opts['boutiques'],
                  opts['reset'], opts['demo_cases'])

    # Rôle : garantit dépôt et boutiques, approvisionne le dépôt, puis distribue par transfert, sans doublon.
    # Liens : appelée par Command.handle ; crée des StockMovement (apps/stock/models.py) et des Transfer.
    # Appelle Transfer.send() et Transfer.receive() (apps/transfers/models.py), qui créent les mouvements de stock.
    @transaction.atomic
    def _run(self, enterprise, units, per_boutique, n_boutiques, reset=False, demo_cases=False):
        from apps.accounts.models import User
        from apps.locations.models import Location, LocationType
        from apps.products.models import Product
        from apps.stock.models import StockMovement, Stock
        from apps.transfers.models import Transfer, TransferItem

        actor = (
            User.objects.filter(enterprise=enterprise, role__in=['admin', 'owner']).first()
            or User.objects.filter(enterprise=enterprise).first()
        )
        if not actor:
            self.stdout.write(self.style.ERROR('No user found for this enterprise.'))
            return

        if reset:
            self._reset_inventory(enterprise)

        # Ensure location types exist.
        wh_type, _ = LocationType.objects.get_or_create(
            enterprise=enterprise, name='Dépôt (Warehouse)', defaults={'behaviour': 'warehouse'})
        bt_type, _ = LocationType.objects.get_or_create(
            enterprise=enterprise, name='Boutique', defaults={'behaviour': 'boutique'})

        # Ensure a main depot.
        depot = Location.objects.filter(enterprise=enterprise, location_type='warehouse', is_active=True).first()
        if not depot:
            depot = Location.objects.create(
                enterprise=enterprise, name='Dépôt Principal', code='WH-MAIN',
                location_type='warehouse', type_ref=wh_type, is_main_warehouse=True,
                is_active=True, created_by=actor,
            )
        self.stdout.write(f'  Depot: {depot.name}')

        # Ensure N active boutiques.
        boutiques = list(Location.objects.filter(
            enterprise=enterprise, location_type='boutique', is_active=True).order_by('name'))
        defaults_names = ['Boutique Centre', 'Boutique Nord', 'Boutique Sud',
                          'Boutique Est', 'Boutique Ouest']
        idx = 0
        while len(boutiques) < n_boutiques and idx < len(defaults_names):
            name = defaults_names[idx]
            idx += 1
            if Location.objects.filter(enterprise=enterprise, name=name).exists():
                continue
            code = 'BT-' + name.split()[-1][:4].upper()
            boutiques.append(Location.objects.create(
                enterprise=enterprise, name=name, code=code,
                location_type='boutique', type_ref=bt_type, is_active=True, created_by=actor,
            ))
        boutiques = boutiques[:n_boutiques]
        self.stdout.write(f'  Boutiques: {", ".join(b.name for b in boutiques)}')

        products = list(Product.objects.filter(enterprise=enterprise, is_active=True).order_by('name'))
        if not products:
            self.stdout.write(self.style.WARNING('  No products. Run seed_catalog first.'))
            return

        # 1) Stock the depot (once per product). Gate on the SCENARIO marker so
        #    unrelated pre-existing initial_stock movements don't make us skip.
        marker_init = 'SCENARIO_INIT'
        entries = 0
        for product in products:
            already = StockMovement.objects.filter(
                enterprise=enterprise, location=depot, product=product,
                reason='initial_stock', notes=marker_init,
            ).exists()
            if already:
                continue
            StockMovement.objects.create(
                enterprise=enterprise, location=depot, product=product, user=actor,
                movement_type='entry', reason='initial_stock', quantity=Decimal(units),
                unit_cost=product.purchase_price, notes=marker_init,
            )
            entries += 1
        self.stdout.write(self.style.SUCCESS(f'  Depot initial stock: {entries} products @ {units}'))

        # 2) Distribute to each boutique via real transfers (once per boutique).
        transfers_made = 0
        for boutique in boutiques:
            marker = f'SCENARIO:{boutique.code}'
            if Transfer.objects.filter(enterprise=enterprise, destination_location=boutique,
                                       notes=marker).exists():
                continue
            transfer = Transfer.objects.create(
                enterprise=enterprise, source_location=depot, destination_location=boutique,
                status='draft', notes=marker, created_by=actor,
            )
            for product in products:
                TransferItem.objects.create(
                    transfer=transfer, product=product,
                    quantity=Decimal(per_boutique), received_quantity=Decimal(per_boutique),
                    unit_cost=product.purchase_price,
                )
            transfer.send(actor)
            transfer.receive(actor)
            transfers_made += 1
            self.stdout.write(f'    → {boutique.name}: transfer {transfer.reference} (received)')

        self.stdout.write(self.style.SUCCESS(f'  Transfers completed: {transfers_made}'))

        # 3) Optional demo cases: Stock Faible (low) + Rupture (out-of-stock).
        if demo_cases and boutiques and len(products) >= 2:
            self._make_demo_cases(enterprise, boutiques[0], products, actor)

        # Summary.
        depot_total = Stock.objects.filter(enterprise=enterprise, location=depot).aggregate(
            t=Sum('quantity'))['t'] or 0
        self.stdout.write(self.style.SUCCESS(
            f'\n  Depot stock now: {depot_total} units across {len(products)} products'
        ))
        for b in boutiques:
            bt_total = Stock.objects.filter(enterprise=enterprise, location=b).aggregate(
                t=Sum('quantity'))['t'] or 0
            self.stdout.write(f'    {b.name}: {bt_total} units')
        self.stdout.write(self.style.SUCCESS('\n  Scenario ready.\n'))

    # Rôle : efface transferts, mouvements et stocks de l'entreprise ; garde produits, emplacements et utilisateurs.
    # Liens : appelée par Command._run avec --reset ; supprime directement, sans passer par StockMovement.save().
    def _reset_inventory(self, enterprise):
        """Wipe inventory + transfers for the enterprise (keeps products/locations/users)."""
        from apps.locations.models import LocationStock
        from apps.stock.models import Stock, StockMovement
        from apps.transfers.models import Transfer, TransferItem

        TransferItem.objects.filter(transfer__enterprise=enterprise).delete()
        Transfer.objects.filter(enterprise=enterprise).delete()
        StockMovement.objects.filter(enterprise=enterprise).delete()
        Stock.objects.filter(enterprise=enterprise).delete()
        LocationStock.objects.filter(location__enterprise=enterprise).delete()
        self.stdout.write(self.style.WARNING('  Inventory reset (stock, movements, transfers cleared).'))

    # Rôle : amène un produit d'une boutique en stock faible et un autre en rupture, pour la démonstration.
    # Liens : appelée par Command._run avec --demo-cases ; utilise current_qty et drive_to.
    def _make_demo_cases(self, enterprise, boutique, products, actor):
        """Drive two products at a boutique into low-stock and out-of-stock states."""
        from decimal import Decimal
        from apps.locations.models import LocationStock
        from apps.stock.models import StockMovement

        # Rôle : renvoie la quantité du produit dans la boutique, ou 0 si la ligne n'existe pas.
        # Liens : fonction interne appelée par drive_to ; lit LocationStock (apps/locations/models.py).
        def current_qty(product):
            ls = LocationStock.objects.filter(location=boutique, product=product).first()
            return ls.quantity if ls else Decimal('0')

        # Rôle : crée une sortie pour descendre à la quantité cible ; ne fait rien si le stock y est déjà ou en dessous.
        # Liens : appelée par _make_demo_cases ; StockMovement.save() (apps/stock/models.py) met les stocks à jour.
        def drive_to(product, target, reason):
            cur = current_qty(product)
            if cur <= Decimal(target):
                return  # already at/below target -> idempotent
            StockMovement.objects.create(
                enterprise=enterprise, location=boutique, product=product, user=actor,
                movement_type='exit', reason=reason, quantity=cur - Decimal(target),
                notes='SCENARIO_DEMOCASE',
            )

        low_product = products[0]
        out_product = products[1]
        # Low: drive below the product's threshold (or to 5 if no threshold)
        low_target = max(0, (low_product.min_stock_threshold or 10) - 5)
        drive_to(low_product, low_target, 'breakage')
        # Rupture: drive to zero
        drive_to(out_product, 0, 'sale')
        self.stdout.write(self.style.WARNING(
            f'  Demo cases at {boutique.name}: "{low_product.name}" -> stock faible, '
            f'"{out_product.name}" -> rupture.'
        ))
