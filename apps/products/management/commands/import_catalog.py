"""
Import the product catalog from the client's Excel stock list, optionally doing
a FULL RESET first (wipe every product and all the data that references it).

The workbook has one sheet per product family. Each sheet has an identifier
column (CODE N° / N° PIECES), a warehouse-quantity column (QTE MAG) and a unit
price column (P.U.). Layout varies slightly per sheet, so columns are located by
header text rather than fixed positions.

Usage:
    python manage.py import_catalog --enterprise DEMO-ENT              # wipe + import
    python manage.py import_catalog --enterprise DEMO-ENT --dry-run    # preview only
    python manage.py import_catalog --enterprise DEMO-ENT --no-wipe    # import, keep existing
"""
import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import openpyxl

from apps.core.models import Enterprise
from apps.locations.models import Location, LocationStock
from apps.accounts.models import User
from apps.products.models import Category, Product, ProductPackaging
from apps.stock.models import Stock, StockMovement
from apps.pos.models import Sale, SaleItem
from apps.transfers.models import Transfer, TransferItem
from apps.customers.models import Customer, CustomerCredit, CreditPayment

DEFAULT_FILE = os.path.join(
    settings.BASE_DIR, 'apps', 'products', 'data', 'stockcontrollist.xlsx'
)

# Category per sheet, in workbook order.
SHEET_CATEGORIES = [
    'Roulements',
    'Paliers & Roulements montés',
    'Pièces & Accessoires',
]


# Rôle : teste si une cellule est un int ou un float, en excluant les booléens.
# Liens : utilisée localement par Command._parse_sheet.
def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


# Rôle : convertit une cellule en texte de code produit (32209.0 devient « 32209 », vide si None).
# Liens : utilisée localement par Command._parse_sheet.
def _clean_id(v):
    """Turn a cell value into a product name/code string (32209.0 -> '32209')."""
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


# Rôle : convertit une valeur en Decimal, avec 0 pour une valeur vide ou invalide.
# Liens : utilisée localement par Command._parse_sheet pour le prix.
def _to_decimal(v):
    if v is None or v == '':
        return Decimal('0')
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


class Command(BaseCommand):
    help = "Full-reset the catalog and import products from the Excel stock list."

    # Rôle : déclare --file, --enterprise, --location, --no-wipe et --dry-run.
    # Liens : appelée par Django au lancement de la commande ; valeurs lues par Command.handle.
    def add_arguments(self, parser):
        parser.add_argument('--file', default=DEFAULT_FILE, help='Path to the .xlsx file')
        parser.add_argument('--enterprise', default='DEMO-ENT', help='Enterprise code to import into')
        parser.add_argument('--location', default=None, help='Location id or name to receive the stock (default: main/warehouse)')
        parser.add_argument('--no-wipe', action='store_true', help='Import without wiping existing data first')
        parser.add_argument('--dry-run', action='store_true', help='Parse and report only; change nothing')

    # -- parsing -------------------------------------------------------------

    # Rôle : repère l'en-tête d'une feuille (ligne contenant QTE) puis produit un dict nom/quantité/prix par ligne.
    # Liens : appelée par Command.handle pour chaque feuille ; utilise _clean_id, _is_number et _to_decimal.
    def _parse_sheet(self, ws):
        """Yield {'name','qty','price'} dicts for the data rows of one sheet."""
        rows = [list(r) for r in ws.iter_rows(values_only=True)]

        # Locate the header row (the one mentioning QTE).
        header_idx = None
        for i, r in enumerate(rows):
            if any(isinstance(c, str) and 'QTE' in c.upper() for c in r):
                header_idx = i
                break
        if header_idx is None:
            return

        header = rows[header_idx]

        # Rôle : renvoie l'indice de la première colonne dont l'en-tête (majuscules, sans espaces) vérifie le test.
        # Liens : fonction interne, utilisée seulement par Command._parse_sheet.
        def find_col(pred):
            for j, c in enumerate(header):
                if isinstance(c, str) and pred(c.upper().replace(' ', '')):
                    return j
            return None

        id_col = find_col(lambda h: 'CODE' in h or 'PIECE' in h or 'PIÈCE' in h)
        qty_col = find_col(lambda h: 'MAG' in h) or find_col(lambda h: 'QTE' in h)
        price_col = find_col(lambda h: 'P.U' in h or h.startswith('PU'))
        if id_col is None or qty_col is None or price_col is None:
            return

        for r in rows[header_idx + 1:]:
            if id_col >= len(r):
                continue
            name = _clean_id(r[id_col])
            if not name:
                continue  # blank / grand-total row
            if name.upper().replace(' ', '') in ('CODEN°', 'N°PIECES'):
                continue  # a repeated header
            qty = r[qty_col] if qty_col < len(r) and _is_number(r[qty_col]) else 0
            price = r[price_col] if price_col < len(r) and _is_number(r[price_col]) else 0
            yield {'name': name, 'qty': Decimal(str(qty)), 'price': _to_decimal(price)}

    # -- wipe ----------------------------------------------------------------

    # Rôle : efface produits, catégories, ventes, crédits, mouvements, transferts et stocks d'une entreprise.
    # Liens : appelée par Command.handle sauf avec --no-wipe ; remet aussi à zéro les compteurs de Customer.
    # L'ordre des suppressions respecte les clés RESTRICT et PROTECT de ces modèles.
    def _wipe(self, ent):
        """Delete every product for this enterprise and all data referencing it."""
        # Order matters: RESTRICT/PROTECT rows must go before the products they lock.
        # 1) Credits (RESTRICT onto Sale) then sales (cascade SaleItem).
        CreditPayment.objects.filter(credit__customer__enterprise=ent).delete()
        CustomerCredit.objects.filter(customer__enterprise=ent).delete()
        Sale.objects.filter(enterprise=ent).delete()          # cascades SaleItem
        # 2) Stock movements (RESTRICT onto Product).
        StockMovement.objects.filter(enterprise=ent).delete()
        # 3) Transfers (TransferItem PROTECTs Product; cascade via Transfer).
        Transfer.objects.filter(enterprise=ent).delete()      # cascades TransferItem
        # 4) Stock tables.
        Stock.objects.filter(enterprise=ent).delete()
        LocationStock.objects.filter(location__enterprise=ent).delete()
        # 5) Products (cascade ProductPackaging + any remaining Stock/LocationStock).
        Product.objects.filter(enterprise=ent).delete()
        Category.objects.filter(enterprise=ent).delete()
        # 6) Customer running totals now reference deleted sales -> reset to zero.
        Customer.objects.filter(enterprise=ent).update(
            current_balance=0, total_purchases=0, purchase_count=0, loyalty_points=0,
        )

    # -- main ----------------------------------------------------------------

    # Rôle : résout entreprise, emplacement et utilisateur, lit le classeur, puis importe dans une transaction.
    # Liens : python manage.py import_catalog et tests/test_import_catalog.py ; écrit Category et Product.
    # Crée des StockMovement : StockMovement.save() (apps/stock/models.py) met à jour Stock et LocationStock.
    def handle(self, *args, **opts):
        path = opts['file']
        if not os.path.exists(path):
            raise CommandError(f"File not found: {path}")

        try:
            ent = Enterprise.objects.get(code=opts['enterprise'])
        except Enterprise.DoesNotExist:
            codes = ', '.join(Enterprise.objects.values_list('code', flat=True))
            raise CommandError(f"Enterprise '{opts['enterprise']}' not found. Available: {codes}")

        loc_qs = Location.objects.filter(enterprise=ent, is_active=True)
        if opts['location']:
            sel = opts['location']
            warehouse = (
                (loc_qs.filter(pk=sel).first() if str(sel).isdigit() else None)
                or loc_qs.filter(name=sel).first()
            )
            if warehouse is None:
                choices = ', '.join(f"{l.pk}:{l.name}" for l in loc_qs)
                raise CommandError(f"Location '{sel}' not found for {ent.code}. Choices: {choices}")
        else:
            # Prefer the flagged main warehouse, then any warehouse-type location,
            # then any active location (never silently a boutique if a depot exists).
            warehouse = (
                loc_qs.filter(is_main_warehouse=True).first()
                or loc_qs.filter(location_type='warehouse').first()
                or loc_qs.first()
            )
        if warehouse is None:
            raise CommandError(f"No location found for enterprise {ent.code} to receive stock.")

        actor = (
            User.objects.filter(enterprise=ent, role__in=['admin', 'owner']).first()
            or User.objects.filter(enterprise=ent).first()
            or User.objects.filter(is_superuser=True).first()
        )
        if actor is None:
            raise CommandError("No user available to attribute the initial stock movements to.")

        # Parse every sheet.
        wb = openpyxl.load_workbook(path, data_only=True)
        parsed = []  # (category_name, [items])
        for idx, sheet_name in enumerate(wb.sheetnames):
            category = SHEET_CATEGORIES[idx] if idx < len(SHEET_CATEGORIES) else sheet_name
            items = list(self._parse_sheet(wb[sheet_name]))
            parsed.append((category, items))

        total = sum(len(items) for _, items in parsed)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nEnterprise: {ent.name} ({ent.code}) · warehouse: {warehouse.name} · actor: {actor.username}"
        ))
        for category, items in parsed:
            with_stock = sum(1 for it in items if it['qty'] > 0)
            self.stdout.write(f"  {category:32s}: {len(items):4d} products ({with_stock} with stock)")
        self.stdout.write(f"  {'TOTAL':32s}: {total:4d} products")

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING("\nDry run — nothing written."))
            # Show a few examples per sheet.
            for category, items in parsed:
                self.stdout.write(f"\n  e.g. {category}:")
                for it in items[:3]:
                    self.stdout.write(f"     {it['name'][:40]:40s} qty={it['qty']} pu={it['price']}")
            return

        with transaction.atomic():
            if not opts['no_wipe']:
                self.stdout.write("\nWiping existing catalog + referencing data …")
                self._wipe(ent)

            created, stocked = 0, 0
            for category_name, items in parsed:
                category, _ = Category.objects.get_or_create(
                    enterprise=ent, name=category_name,
                    defaults={'is_active': True},
                )
                for it in items:
                    product, was_created = Product.objects.get_or_create(
                        enterprise=ent, name=it['name'],
                        defaults={
                            'category': category,
                            'sku': it['name'][:50],
                            'unit': 'piece',
                            'purchase_price': it['price'],
                            'sale_price': it['price'],  # sale = cost, edited later
                            'tax_rate': Decimal('0'),
                            'min_stock_threshold': 0,
                            'is_active': True,
                        },
                    )
                    if was_created:
                        created += 1
                    # Initial stock (QTE MAG) at the main warehouse — the save()
                    # on StockMovement updates Stock + LocationStock automatically.
                    if it['qty'] and it['qty'] > 0:
                        StockMovement.objects.create(
                            product=product, user=actor, enterprise=ent,
                            location=warehouse, movement_type='entry',
                            reason='initial_stock', quantity=it['qty'],
                            unit_cost=it['price'],
                            reference='Import stock 31/12/2024',
                        )
                        stocked += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} products created, {stocked} initial-stock entries at {warehouse.name}."
        ))
        # Report the resulting stock value as a sanity check.
        value = Decimal('0')
        for qty, pp in Stock.objects.filter(enterprise=ent).values_list('quantity', 'product__purchase_price'):
            value += (qty or 0) * (pp or 0)
        self.stdout.write(f"Total stock value now: {value:,.0f} FB")
