"""
End-to-end tests for the Stock Entry product dropdown fix.

Covers:
- The searchable product combobox markup is rendered when products exist.
- The product JSON payload that powers the search is correct.
- The empty-state (no products) is shown with the right call-to-action per role.
- A stock entry can still be submitted (hidden `product` input round-trips).
- The `seed_catalog` management command populates an existing enterprise and is idempotent.
"""
import pytest
from decimal import Decimal
from io import StringIO

from django.test import Client
from django.urls import reverse
from django.core.management import call_command

from apps.core.models import Enterprise
from apps.locations.models import Location
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement

from tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def enterprise():
    return Enterprise.objects.create(name='Hema Test', code='HEMATEST', currency='FB')


@pytest.fixture
def warehouse(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Dépôt Principal', code='WH001',
        location_type='warehouse', is_main_warehouse=True,
    )


@pytest.fixture
def admin_user(enterprise, warehouse):
    return UserFactory(role='admin', enterprise=enterprise, location=warehouse)


@pytest.fixture
def stock_manager_user(enterprise, warehouse):
    return UserFactory(role='stock_manager', enterprise=enterprise, location=warehouse)


def login(user):
    client = Client()
    client.force_login(user)
    return client


def make_product(enterprise, name='Coca-Cola 50cl', category_name='Boissons'):
    category = Category.objects.create(name=category_name, enterprise=enterprise)
    return Product.objects.create(
        name=name, category=category, unit='piece',
        purchase_price=Decimal('800'), sale_price=Decimal('1000'),
        enterprise=enterprise,
    )


# ---------------------------------------------------------------------------
# Searchable dropdown rendering
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSearchableDropdown:

    def test_combobox_rendered_when_products_exist(self, admin_user, enterprise):
        make_product(enterprise)
        client = login(admin_user)
        html = client.get(reverse('stock:entry')).content.decode()

        # Alpine component + JSON payload + searchable input + hidden field
        assert 'stockEntryForm(' in html
        assert 'id="products-data"' in html
        assert 'Rechercher un produit' in html
        assert 'name="product"' in html
        # No legacy empty <select> placeholder
        assert 'Sélectionnez un produit' not in html

    def test_preselected_product_via_query_param(self, admin_user, enterprise):
        product = make_product(enterprise, name='Coca 33cl')
        client = login(admin_user)
        html = client.get(reverse('stock:entry') + f'?product={product.pk}').content.decode()
        # The pk is handed to the Alpine component so it preselects + fills cost
        assert f"stockEntryForm('{product.pk}')" in html
        # Purchase price is embedded so the unit cost can auto-fill
        assert '"price"' in html

    def test_product_label_in_json_payload(self, admin_user, enterprise):
        make_product(enterprise, name='Fanta Orange 50cl', category_name='Boissons')
        client = login(admin_user)
        html = client.get(reverse('stock:entry')).content.decode()
        # The json_script payload embeds the searchable label
        assert 'Fanta Orange 50cl' in html
        assert 'Boissons' in html

    def test_only_active_enterprise_products_in_payload(self, admin_user, enterprise):
        make_product(enterprise, name='Visible Product')
        # Inactive product must not appear
        cat = Category.objects.create(name='Autre', enterprise=enterprise)
        Product.objects.create(
            name='Hidden Inactive', category=cat, unit='piece',
            purchase_price=Decimal('1'), sale_price=Decimal('2'),
            enterprise=enterprise, is_active=False,
        )
        # Product from another enterprise must not appear
        other = Enterprise.objects.create(name='Other', code='OTHER', currency='FB')
        make_product(other, name='Foreign Product')

        client = login(admin_user)
        html = client.get(reverse('stock:entry')).content.decode()
        assert 'Visible Product' in html
        assert 'Hidden Inactive' not in html
        assert 'Foreign Product' not in html


# ---------------------------------------------------------------------------
# Empty-state
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmptyState:

    def test_empty_state_shown_when_no_products(self, admin_user):
        client = login(admin_user)
        html = client.get(reverse('stock:entry')).content.decode()
        assert 'Aucun produit disponible' in html
        # No form / combobox when there is nothing to pick
        assert 'stockEntryForm(' not in html

    def test_admin_sees_create_product_cta(self, admin_user):
        client = login(admin_user)
        html = client.get(reverse('stock:entry')).content.decode()
        assert reverse('products:product_create') in html
        assert 'Créer un produit' in html

    def test_stock_manager_sees_contact_admin_message(self, stock_manager_user):
        # stock_manager cannot create products -> no create link, contact message instead
        client = login(stock_manager_user)
        html = client.get(reverse('stock:entry')).content.decode()
        assert 'Aucun produit disponible' in html
        assert 'Contactez un administrateur' in html
        assert reverse('products:product_create') not in html


# ---------------------------------------------------------------------------
# Submission still works through the hidden input
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubmissionStillWorks:

    def test_post_creates_movement_and_updates_stock(self, stock_manager_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {
            'product': product.pk,
            'quantity': '40',
            'unit_cost': '800',
            'reason': 'purchase',
            'location': warehouse.pk,
        })
        assert resp.status_code == 302
        movement = StockMovement.objects.get(product=product)
        assert movement.movement_type == 'entry'
        assert movement.quantity == Decimal('40')
        assert Stock.objects.get(product=product, location=warehouse).quantity == Decimal('40')


# ---------------------------------------------------------------------------
# Invalid submissions are rejected with a readable French message, never with
# a raw Django "Field 'id' expected a number but got ''." ValueError.
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEntryValidation:

    def _messages(self, response):
        return [str(m) for m in response.context['messages']]

    def test_empty_product_shows_friendly_error(self, stock_manager_user, enterprise, warehouse):
        make_product(enterprise)
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {
            'product': '', 'quantity': '10', 'reason': 'purchase', 'location': warehouse.pk,
        })
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0
        messages = self._messages(resp)
        assert any('sélectionner un produit' in m for m in messages)
        assert not any("expected a number" in m for m in messages)

    def test_non_numeric_product_rejected(self, stock_manager_user, enterprise):
        make_product(enterprise)
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {'product': 'abc', 'quantity': '10', 'reason': 'purchase'})
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0

    def test_empty_quantity_rejected(self, stock_manager_user, enterprise):
        product = make_product(enterprise)
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {'product': product.pk, 'quantity': '', 'reason': 'purchase'})
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0
        assert any('Quantité invalide' in m for m in self._messages(resp))

    def test_zero_quantity_rejected(self, stock_manager_user, enterprise):
        product = make_product(enterprise)
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {'product': product.pk, 'quantity': '0', 'reason': 'purchase'})
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0

    def test_product_from_another_enterprise_rejected(self, stock_manager_user):
        other = Enterprise.objects.create(name='Other', code='OTHER2', currency='FB')
        foreign = make_product(other, name='Foreign Product')
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {'product': foreign.pk, 'quantity': '5', 'reason': 'purchase'})
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0

    def test_location_from_another_enterprise_rejected(self, stock_manager_user, enterprise):
        product = make_product(enterprise)
        other = Enterprise.objects.create(name='Other', code='OTHER3', currency='FB')
        foreign_loc = Location.objects.create(
            enterprise=other, name='Dépôt Etranger', code='WH999', location_type='warehouse',
        )
        client = login(stock_manager_user)
        resp = client.post(reverse('stock:entry'), {
            'product': product.pk, 'quantity': '5', 'reason': 'purchase', 'location': foreign_loc.pk,
        })
        assert resp.status_code == 200
        assert StockMovement.objects.count() == 0

    def test_submit_button_disabled_until_product_selected(self, stock_manager_user, enterprise):
        make_product(enterprise)
        client = login(stock_manager_user)
        html = client.get(reverse('stock:entry')).content.decode()
        assert ':disabled="!selectedId"' in html
        # `required` on a hidden input is ignored by browsers — must not be relied on
        assert 'name="product" :value="selectedId" required' not in html


# ---------------------------------------------------------------------------
# seed_catalog management command
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSeedCatalogCommand:

    def test_seeds_existing_enterprise(self, enterprise):
        assert Product.objects.filter(enterprise=enterprise).count() == 0
        call_command('seed_catalog', stdout=StringIO())
        assert Category.objects.filter(enterprise=enterprise).count() > 0
        assert Product.objects.filter(enterprise=enterprise).count() > 0

    def test_is_idempotent(self, enterprise):
        out = StringIO()
        call_command('seed_catalog', stdout=out)
        first_count = Product.objects.filter(enterprise=enterprise).count()
        call_command('seed_catalog', stdout=out)
        assert Product.objects.filter(enterprise=enterprise).count() == first_count

    def test_enterprise_filter(self):
        target = Enterprise.objects.create(name='Target', code='TGT', currency='FB')
        other = Enterprise.objects.create(name='Skip', code='SKIP', currency='FB')
        call_command('seed_catalog', '--enterprise', 'TGT', stdout=StringIO())
        assert Product.objects.filter(enterprise=target).count() > 0
        assert Product.objects.filter(enterprise=other).count() == 0

    def test_with_stock_flag_creates_stock_rows(self, enterprise, warehouse):
        call_command('seed_catalog', '--with-stock', stdout=StringIO())
        products = Product.objects.filter(enterprise=enterprise)
        assert products.count() > 0
        # Every seeded product gets a stock row at the main warehouse (qty 0)
        assert Stock.objects.filter(enterprise=enterprise, location=warehouse).count() == products.count()


@pytest.mark.django_db
class TestEmplacementLock:

    def test_emplacement_locked_when_location_in_url(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        html = client.get(reverse('stock:entry') + f'?product={product.pk}&location={warehouse.pk}').content.decode()
        # Location is carried as a hidden input; the dropdown is NOT rendered
        assert f'name="location" value="{warehouse.pk}"' in html
        assert 'Dépôt Principal' in html
        assert '<select name="location"' not in html

    def test_emplacement_dropdown_when_no_location_param(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        html = client.get(reverse('stock:entry') + f'?product={product.pk}').content.decode()
        assert '<select name="location"' in html

    def test_locked_emplacement_round_trips_on_submit(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        resp = client.post(reverse('stock:entry'), {
            'product': product.pk, 'quantity': '7', 'reason': 'purchase',
            'location': warehouse.pk,
        })
        assert resp.status_code in (302, 200)
        mv = StockMovement.objects.filter(product=product, location=warehouse).first()
        assert mv is not None and mv.quantity == Decimal('7')


@pytest.mark.django_db
class TestEntryNextRedirect:

    def test_redirects_to_next_after_save(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        resp = client.post(reverse('stock:entry'), {
            'product': product.pk, 'quantity': '3', 'reason': 'purchase',
            'location': warehouse.pk, 'next': '/locations/2/?next=/products/5/',
        })
        assert resp.status_code == 302
        assert resp['Location'] == '/locations/2/?next=/products/5/'

    def test_external_next_rejected(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        resp = client.post(reverse('stock:entry'), {
            'product': product.pk, 'quantity': '3', 'reason': 'purchase',
            'location': warehouse.pk, 'next': 'https://evil.com/x',
        })
        assert resp.status_code == 302
        assert 'evil.com' not in resp['Location']

    def test_form_carries_next_hidden_field(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise)
        client = login(admin_user)
        html = client.get(reverse('stock:entry') + f'?product={product.pk}&next=/locations/2/').content.decode()
        assert 'name="next" value="/locations/2/"' in html
