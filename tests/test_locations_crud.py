"""
End-to-end tests for Location (Emplacement) CRUD + manageable LocationType:
create/edit/delete locations (with type behaviour mapping) and type management.
"""
import pytest
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from apps.core.models import Enterprise
from apps.locations.models import Location, LocationType
from apps.products.models import Category, Product
from apps.stock.models import Stock

from tests.factories import UserFactory


@pytest.fixture
def enterprise():
    return Enterprise.objects.create(name='Hema Test', code='HEMATEST', currency='FB')


@pytest.fixture
def types(enterprise):
    """The two default location types for the enterprise."""
    wh = LocationType.objects.create(enterprise=enterprise, name='Dépôt (Warehouse)', behaviour='warehouse')
    bt = LocationType.objects.create(enterprise=enterprise, name='Boutique', behaviour='boutique')
    return {'warehouse': wh, 'boutique': bt}


@pytest.fixture
def admin_user(enterprise):
    return UserFactory(role='admin', enterprise=enterprise)


@pytest.fixture
def cashier_user(enterprise):
    return UserFactory(role='cashier', enterprise=enterprise)


def login(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestLocationCreate:

    def test_dashboard_shows_create_and_types_buttons(self, admin_user):
        html = login(admin_user).get(reverse('locations:dashboard')).content.decode()
        assert reverse('locations:create') in html
        assert 'Nouvel emplacement' in html
        assert reverse('locations:type_list') in html
        assert 'Gérer les types' in html

    def test_create_form_lists_managed_types(self, admin_user, types):
        html = login(admin_user).get(reverse('locations:create')).content.decode()
        assert 'name="type_id"' in html
        assert 'Boutique' in html
        assert 'Dépôt (Warehouse)' in html

    def test_create_warehouse(self, admin_user, enterprise, types):
        resp = login(admin_user).post(reverse('locations:create'), {
            'name': 'Dépôt Nord', 'code': 'WH-NORD', 'type_id': types['warehouse'].pk, 'is_active': 'on',
        })
        assert resp.status_code == 302
        loc = Location.objects.get(code='WH-NORD')
        assert loc.location_type == 'warehouse'          # behaviour mapped
        assert loc.type_ref == types['warehouse']        # custom type kept
        assert loc.created_by == admin_user

    def test_create_boutique(self, admin_user, types):
        resp = login(admin_user).post(reverse('locations:create'), {
            'name': 'Boutique Sud', 'code': 'BT-SUD', 'type_id': types['boutique'].pk, 'is_active': 'on',
        })
        assert resp.status_code == 302
        assert Location.objects.get(code='BT-SUD').location_type == 'boutique'

    def test_create_with_custom_type(self, admin_user, enterprise):
        pharma = LocationType.objects.create(enterprise=enterprise, name='Pharmacie', behaviour='boutique')
        resp = login(admin_user).post(reverse('locations:create'), {
            'name': 'Pharma 1', 'code': 'PH-1', 'type_id': pharma.pk, 'is_active': 'on',
        })
        assert resp.status_code == 302
        loc = Location.objects.get(code='PH-1')
        assert loc.type_ref == pharma
        assert loc.location_type == 'boutique'           # behaves as boutique
        assert loc.type_display == 'Pharmacie'

    def test_invalid_type_rejected(self, admin_user, types):
        resp = login(admin_user).post(reverse('locations:create'), {
            'name': 'X', 'code': 'X1', 'type_id': '99999', 'is_active': 'on',
        })
        assert resp.status_code == 200
        assert not Location.objects.filter(code='X1').exists()

    def test_cashier_cannot_create(self, cashier_user):
        resp = login(cashier_user).get(reverse('locations:create'))
        assert resp.status_code == 302
        assert Location.objects.count() == 0


@pytest.mark.django_db
class TestLocationEdit:

    def test_edit_changes_name_and_type(self, admin_user, enterprise, types):
        loc = Location.objects.create(enterprise=enterprise, name='Ancien', code='C1',
                                      location_type='boutique', type_ref=types['boutique'])
        resp = login(admin_user).post(reverse('locations:edit', args=[loc.pk]), {
            'name': 'Nouveau Nom', 'code': 'C1', 'type_id': types['warehouse'].pk, 'is_active': 'on',
        })
        assert resp.status_code == 302
        loc.refresh_from_db()
        assert loc.name == 'Nouveau Nom'
        assert loc.type_ref == types['warehouse']
        assert loc.location_type == 'warehouse'

    def test_detail_shows_edit_button(self, admin_user, enterprise, types):
        loc = Location.objects.create(enterprise=enterprise, name='D', code='D1',
                                      location_type='boutique', type_ref=types['boutique'])
        html = login(admin_user).get(reverse('locations:detail', args=[loc.pk])).content.decode()
        assert reverse('locations:edit', args=[loc.pk]) in html

    def test_inactive_location_still_listed_on_dashboard(self, admin_user, enterprise, types):
        """An inactive location must remain visible/manageable (not vanish)."""
        loc = Location.objects.create(enterprise=enterprise, name='Prospect', code='PROS1',
                                      location_type='warehouse', type_ref=types['warehouse'],
                                      is_active=False)
        html = login(admin_user).get(reverse('locations:dashboard')).content.decode()
        assert 'Prospect' in html
        assert 'Inactif' in html
        assert reverse('locations:detail', args=[loc.pk]) in html

    def test_reactivate_via_edit(self, admin_user, enterprise, types):
        loc = Location.objects.create(enterprise=enterprise, name='Re', code='RE1',
                                      location_type='warehouse', type_ref=types['warehouse'], is_active=False)
        login(admin_user).post(reverse('locations:edit', args=[loc.pk]), {
            'name': 'Re', 'code': 'RE1', 'type_id': types['warehouse'].pk, 'is_active': 'on',
        })
        loc.refresh_from_db()
        assert loc.is_active is True


@pytest.mark.django_db
class TestLocationDelete:

    def test_delete_empty_location(self, admin_user, enterprise, types):
        loc = Location.objects.create(enterprise=enterprise, name='Empty', code='E1',
                                      location_type='boutique', type_ref=types['boutique'])
        resp = login(admin_user).post(reverse('locations:delete', args=[loc.pk]))
        assert resp.status_code == 302
        assert not Location.objects.filter(pk=loc.pk).exists()

    def test_delete_blocked_when_has_stock(self, admin_user, enterprise, types):
        loc = Location.objects.create(enterprise=enterprise, name='Full', code='F1',
                                      location_type='warehouse', type_ref=types['warehouse'])
        cat = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(name='P', category=cat, unit='piece',
                                         purchase_price=Decimal('1'), sale_price=Decimal('2'), enterprise=enterprise)
        Stock.objects.create(enterprise=enterprise, location=loc, product=product, quantity=Decimal('5'))
        resp = login(admin_user).post(reverse('locations:delete', args=[loc.pk]))
        assert resp.status_code == 302
        assert Location.objects.filter(pk=loc.pk).exists()


@pytest.mark.django_db
class TestLocationTypeManagement:

    def test_type_list_renders(self, admin_user, types):
        html = login(admin_user).get(reverse('locations:type_list')).content.decode()
        assert 'Boutique' in html
        assert 'Dépôt (Warehouse)' in html
        assert reverse('locations:type_create') in html

    def test_create_custom_type(self, admin_user, enterprise):
        resp = login(admin_user).post(reverse('locations:type_create'), {
            'name': 'Pharmacie', 'behaviour': 'boutique', 'is_active': 'on',
        })
        assert resp.status_code == 302
        t = LocationType.objects.get(enterprise=enterprise, name='Pharmacie')
        assert t.behaviour == 'boutique'

    def test_duplicate_type_name_rejected(self, admin_user, types):
        resp = login(admin_user).post(reverse('locations:type_create'), {
            'name': 'Boutique', 'behaviour': 'boutique', 'is_active': 'on',
        })
        assert resp.status_code == 200
        assert LocationType.objects.filter(name='Boutique').count() == 1

    def test_edit_type_syncs_location_behaviour(self, admin_user, enterprise):
        t = LocationType.objects.create(enterprise=enterprise, name='Kiosque', behaviour='boutique')
        loc = Location.objects.create(enterprise=enterprise, name='K1', code='K1',
                                      location_type='boutique', type_ref=t)
        # Change the type's behaviour to warehouse -> dependent location should follow
        login(admin_user).post(reverse('locations:type_edit', args=[t.pk]), {
            'name': 'Kiosque', 'behaviour': 'warehouse', 'is_active': 'on',
        })
        loc.refresh_from_db()
        assert loc.location_type == 'warehouse'

    def test_delete_unused_type(self, admin_user, enterprise):
        t = LocationType.objects.create(enterprise=enterprise, name='Temp', behaviour='boutique')
        resp = login(admin_user).post(reverse('locations:type_delete', args=[t.pk]))
        assert resp.status_code == 302
        assert not LocationType.objects.filter(pk=t.pk).exists()

    def test_delete_type_in_use_blocked(self, admin_user, enterprise, types):
        Location.objects.create(enterprise=enterprise, name='Uses BT', code='UB1',
                                location_type='boutique', type_ref=types['boutique'])
        resp = login(admin_user).post(reverse('locations:type_delete', args=[types['boutique'].pk]))
        assert resp.status_code == 302
        assert LocationType.objects.filter(pk=types['boutique'].pk).exists()  # not deleted
