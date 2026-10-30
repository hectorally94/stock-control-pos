"""
Multi-location inventory consistency tests.

These guard the core invariant uncovered while testing the depot→boutiques
scenario: the `Stock` table (read by the stock dashboard) and the
`LocationStock` table (read by the locations dashboard + reports) must ALWAYS
agree, because entries, transfers and sales all flow through StockMovement.
"""
import pytest
from decimal import Decimal

from django.test import Client
from django.urls import reverse
from django.core.management import call_command
from io import StringIO

from apps.core.models import Enterprise
from apps.locations.models import Location, LocationType, LocationStock
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement
from apps.transfers.models import Transfer, TransferItem
from apps.pos.models import Sale, SaleItem

from tests.factories import UserFactory


@pytest.fixture
def enterprise():
    return Enterprise.objects.create(name='Hema Test', code='HEMATEST', currency='FB')


@pytest.fixture
def admin_user(enterprise):
    return UserFactory(role='admin', enterprise=enterprise)


@pytest.fixture
def depot(enterprise):
    wh = LocationType.objects.create(enterprise=enterprise, name='Dépôt', behaviour='warehouse')
    return Location.objects.create(enterprise=enterprise, name='Dépôt Principal', code='WH1',
                                   location_type='warehouse', type_ref=wh, is_main_warehouse=True)


@pytest.fixture
def boutiques(enterprise):
    bt = LocationType.objects.create(enterprise=enterprise, name='Boutique', behaviour='boutique')
    return [
        Location.objects.create(enterprise=enterprise, name=f'Boutique {i}', code=f'BT{i}',
                                location_type='boutique', type_ref=bt)
        for i in range(1, 4)
    ]


@pytest.fixture
def product(enterprise):
    cat = Category.objects.create(name='Cat', enterprise=enterprise)
    return Product.objects.create(name='Coca', category=cat, unit='piece',
                                  purchase_price=Decimal('800'), sale_price=Decimal('1000'),
                                  enterprise=enterprise)


def _stock(enterprise, location, product):
    s = Stock.objects.filter(enterprise=enterprise, location=location, product=product).first()
    return s.quantity if s else Decimal('0')


def _locstock(location, product):
    ls = LocationStock.objects.filter(location=location, product=product).first()
    return ls.quantity if ls else Decimal('0')


@pytest.mark.django_db
class TestInventoryConsistency:

    def test_entry_updates_both_tables(self, enterprise, admin_user, depot, product):
        StockMovement.objects.create(
            enterprise=enterprise, location=depot, product=product, user=admin_user,
            movement_type='entry', reason='initial_stock', quantity=Decimal('500'),
        )
        assert _stock(enterprise, depot, product) == Decimal('500')
        assert _locstock(depot, product) == Decimal('500')   # both in sync

    def test_transfer_moves_stock_consistently(self, enterprise, admin_user, depot, boutiques, product):
        # Stock depot with 500
        StockMovement.objects.create(
            enterprise=enterprise, location=depot, product=product, user=admin_user,
            movement_type='entry', reason='initial_stock', quantity=Decimal('500'),
        )
        b = boutiques[0]
        transfer = Transfer.objects.create(
            enterprise=enterprise, source_location=depot, destination_location=b,
            status='draft', created_by=admin_user,
        )
        TransferItem.objects.create(transfer=transfer, product=product, quantity=Decimal('50'))
        transfer.send(admin_user)
        transfer.receive(admin_user)

        # Depot reduced and boutique increased -- in BOTH tables.
        assert _stock(enterprise, depot, product) == Decimal('450')
        assert _locstock(depot, product) == Decimal('450')
        assert _stock(enterprise, b, product) == Decimal('50')
        assert _locstock(b, product) == Decimal('50')

    def test_sale_reduces_boutique_stock_in_both_tables(self, enterprise, admin_user, depot, boutiques, product):
        b = boutiques[0]
        # Put 50 at the boutique via a transfer
        StockMovement.objects.create(
            enterprise=enterprise, location=depot, product=product, user=admin_user,
            movement_type='entry', reason='initial_stock', quantity=Decimal('500'))
        t = Transfer.objects.create(enterprise=enterprise, source_location=depot,
                                    destination_location=b, status='draft', created_by=admin_user)
        TransferItem.objects.create(transfer=t, product=product, quantity=Decimal('50'))
        t.send(admin_user); t.receive(admin_user)

        # Sell 5 at the boutique
        sale = Sale.objects.create(
            enterprise=enterprise, location=b, sale_number='S-1', user=admin_user,
            subtotal=Decimal('5000'), total_amount=Decimal('5000'), amount_paid=Decimal('5000'),
            payment_method='cash', status='completed',
        )
        SaleItem.objects.create(sale=sale, product=product, product_name='Coca',
                                quantity=Decimal('5'), unit_price=Decimal('1000'),
                                purchase_price=Decimal('800'), total_price=Decimal('5000'))

        assert _stock(enterprise, b, product) == Decimal('45')
        assert _locstock(b, product) == Decimal('45')   # locations dashboard sees the sale too

    def test_insufficient_stock_blocks_transfer(self, enterprise, admin_user, depot, boutiques, product):
        b = boutiques[0]
        # Only 10 in depot, try to transfer 50
        StockMovement.objects.create(
            enterprise=enterprise, location=depot, product=product, user=admin_user,
            movement_type='entry', reason='initial_stock', quantity=Decimal('10'))
        t = Transfer.objects.create(enterprise=enterprise, source_location=depot,
                                    destination_location=b, status='draft', created_by=admin_user)
        TransferItem.objects.create(transfer=t, product=product, quantity=Decimal('50'))
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            t.send(admin_user)
        # nothing moved
        assert _stock(enterprise, depot, product) == Decimal('10')


@pytest.mark.django_db
class TestSeedScenarioCommand:

    def test_scenario_conserves_stock(self, enterprise, admin_user, depot, boutiques):
        # catalog
        cat = Category.objects.create(name='C', enterprise=enterprise)
        for i in range(5):
            Product.objects.create(name=f'P{i}', category=cat, unit='piece',
                                   purchase_price=Decimal('100'), sale_price=Decimal('150'),
                                   enterprise=enterprise)

        call_command('seed_scenario', '--units', '500', '--per-boutique', '50',
                     '--boutiques', '3', stdout=StringIO())

        products = Product.objects.filter(enterprise=enterprise)
        for p in products:
            depot_q = _stock(enterprise, depot, p)
            distributed = sum(_stock(enterprise, b, p) for b in boutiques)
            # 500 in, 3x50 out to boutiques -> 350 left, 150 distributed, conserved
            assert depot_q == Decimal('350')
            assert distributed == Decimal('150')
            # Stock and LocationStock agree everywhere
            assert _locstock(depot, p) == depot_q
            for b in boutiques:
                assert _locstock(b, p) == _stock(enterprise, b, p)

    def test_demo_cases_create_low_and_rupture(self, enterprise, admin_user, depot, boutiques):
        cat = Category.objects.create(name='C', enterprise=enterprise)
        p_low = Product.objects.create(name='AAA Low', category=cat, unit='piece',
                                       purchase_price=Decimal('1'), sale_price=Decimal('2'),
                                       enterprise=enterprise, min_stock_threshold=10)
        p_out = Product.objects.create(name='BBB Out', category=cat, unit='piece',
                                       purchase_price=Decimal('1'), sale_price=Decimal('2'),
                                       enterprise=enterprise, min_stock_threshold=10)
        call_command('seed_scenario', '--demo-cases', stdout=StringIO())
        b = boutiques[0]  # demo cases target the first boutique
        # First product alphabetically -> low (below threshold, >0); second -> rupture (0)
        assert 0 < _locstock(b, p_low) < 10
        assert _stock(enterprise, b, p_low) == _locstock(b, p_low)   # tables agree
        assert _locstock(b, p_out) == Decimal('0')

    def test_scenario_idempotent(self, enterprise, admin_user, depot, boutiques):
        cat = Category.objects.create(name='C', enterprise=enterprise)
        Product.objects.create(name='P', category=cat, unit='piece',
                               purchase_price=Decimal('100'), sale_price=Decimal('150'),
                               enterprise=enterprise)
        call_command('seed_scenario', stdout=StringIO())
        call_command('seed_scenario', stdout=StringIO())  # second run must not double
        p = Product.objects.get(name='P')
        assert _stock(enterprise, depot, p) == Decimal('350')  # not 700
