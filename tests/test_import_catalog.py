"""
Tests for the `import_catalog` management command (full-reset + Excel import).

Uses the real bundled workbook (apps/products/data/stockcontrollist.xlsx) so the
parser is exercised against the actual client data.
"""
import pytest
from decimal import Decimal
from io import StringIO

from django.core.management import call_command

from apps.core.models import Enterprise
from apps.locations.models import Location
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement
from tests.factories import UserFactory


@pytest.fixture
def demo(db):
    ent = Enterprise.objects.create(name='Entreprise Demo', code='DEMO-ENT', currency='FB')
    wh = Location.objects.create(
        enterprise=ent, name='Dépôt Principal', code='WH001',
        location_type='warehouse', is_main_warehouse=True,
    )
    UserFactory(role='owner', enterprise=ent, location=wh)
    return ent, wh


def run(**kw):
    call_command('import_catalog', '--enterprise', 'DEMO-ENT', stdout=StringIO(), **kw)


@pytest.mark.django_db
class TestImportCatalog:

    def test_creates_three_categories(self, demo):
        run()
        ent, _ = demo
        names = set(Category.objects.filter(enterprise=ent).values_list('name', flat=True))
        assert names == {'Roulements', 'Paliers & Roulements montés', 'Pièces & Accessoires'}

    def test_imports_all_products_with_stock(self, demo):
        run()
        ent, wh = demo
        # ~340-346 depending on how the DB collates duplicate codes; be tolerant.
        assert Product.objects.filter(enterprise=ent).count() >= 339
        # A known item from each sheet exists, priced as cost=sale.
        p = Product.objects.get(enterprise=ent, name='6000-2RS')
        assert p.purchase_price == p.sale_price == Decimal('15000')
        assert p.category.name == 'Roulements'
        assert p.unit == 'piece'
        # Initial stock landed at the main warehouse.
        assert Stock.objects.filter(enterprise=ent, product=p, location=wh).first().quantity == Decimal('10')
        assert StockMovement.objects.filter(enterprise=ent, reason='initial_stock').count() >= 339

    def test_full_reset_wipes_previous_catalog(self, demo):
        ent, wh = demo
        # Pre-existing product + a RESTRICT-protected movement that the wipe must clear.
        cat = Category.objects.create(enterprise=ent, name='Ancienne catégorie')
        old = Product.objects.create(
            enterprise=ent, category=cat, name='VIEUX PRODUIT', unit='piece',
            purchase_price=Decimal('1'), sale_price=Decimal('2'),
        )
        StockMovement.objects.create(
            product=old, user=ent.users.first() if hasattr(ent, 'users') else UserFactory(enterprise=ent),
            enterprise=ent, location=wh, movement_type='entry', reason='purchase',
            quantity=Decimal('5'),
        )
        run()
        assert not Product.objects.filter(enterprise=ent, name='VIEUX PRODUIT').exists()
        assert not Category.objects.filter(enterprise=ent, name='Ancienne catégorie').exists()

    def test_other_enterprise_untouched(self, demo):
        other = Enterprise.objects.create(name='Autre', code='OTHER', currency='FB')
        ocat = Category.objects.create(enterprise=other, name='Cat')
        Product.objects.create(
            enterprise=other, category=ocat, name='FOREIGN', unit='piece',
            purchase_price=Decimal('1'), sale_price=Decimal('1'),
        )
        run()
        assert Product.objects.filter(enterprise=other).count() == 1
        assert Product.objects.filter(enterprise=other, name='FOREIGN').exists()

    def test_dry_run_writes_nothing(self, demo):
        ent, _ = demo
        run(dry_run=True)
        assert Product.objects.filter(enterprise=ent).count() == 0
