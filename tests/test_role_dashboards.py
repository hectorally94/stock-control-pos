"""
Tests for the role-specific dashboards and the grouped sidebar.

Covers:
- `/` dispatches each role to the right dashboard (Patron / Gérant / Caisse /
  Comptabilité), and stock-only roles to the stock dashboard.
- Each dashboard renders 200 for a user of its role.
- The role guard bounces a user out of a dashboard they may not see.
- The sidebar filters its groups by role.
"""
import pytest
from django.test import Client
from django.urls import reverse

from apps.core.models import Enterprise
from apps.locations.models import Location
from tests.factories import UserFactory


@pytest.fixture
def enterprise(db):
    return Enterprise.objects.create(name='Dash Test', code='DASHT', currency='FB')


@pytest.fixture
def boutique(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Boutique Centre', code='BC001',
        location_type='boutique',
    )


def user(enterprise, role, location=None):
    return UserFactory(role=role, enterprise=enterprise, location=location)


def login(u):
    c = Client()
    c.force_login(u)
    return c


# ---------------------------------------------------------------------------
# Home dispatch
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHomeDispatch:

    @pytest.mark.parametrize('role,expected', [
        ('admin', 'dashboards:patron'),
        ('owner', 'dashboards:patron'),
        ('manager', 'dashboards:gerant'),
        ('boutique_manager', 'dashboards:gerant'),
        ('cashier', 'dashboards:caisse'),
        ('accountant', 'dashboards:comptable'),
    ])
    def test_home_redirects_to_role_dashboard(self, enterprise, role, expected):
        c = login(user(enterprise, role))
        r = c.get(reverse('home'))
        assert r.status_code == 302
        assert r['Location'] == reverse(expected)

    @pytest.mark.parametrize('role', ['warehouse_manager', 'stock_manager'])
    def test_stock_roles_land_on_stock_dashboard(self, enterprise, role):
        c = login(user(enterprise, role))
        r = c.get(reverse('home'))
        assert r.status_code == 302
        assert r['Location'] == reverse('stock:dashboard')

    def test_user_without_enterprise_gets_landing(self, db):
        c = login(UserFactory(role='admin'))  # no enterprise
        r = c.get(reverse('home'))
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Each dashboard renders for its role
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDashboardsRender:

    def test_patron(self, enterprise):
        c = login(user(enterprise, 'owner'))
        r = c.get(reverse('dashboards:patron'))
        assert r.status_code == 200
        assert 'Patron' in r.content.decode()

    def test_gerant(self, enterprise, boutique):
        c = login(user(enterprise, 'boutique_manager', location=boutique))
        r = c.get(reverse('dashboards:gerant'))
        assert r.status_code == 200
        assert 'Gérant' in r.content.decode()

    def test_caisse(self, enterprise, boutique):
        c = login(user(enterprise, 'cashier', location=boutique))
        r = c.get(reverse('dashboards:caisse'))
        assert r.status_code == 200
        assert 'Ma journée' in r.content.decode()

    def test_comptable(self, enterprise):
        c = login(user(enterprise, 'accountant'))
        r = c.get(reverse('dashboards:comptable'))
        assert r.status_code == 200
        assert 'Comptabilité' in r.content.decode()


# ---------------------------------------------------------------------------
# Role guard: wrong role is bounced to its own dashboard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDashboardGuard:

    def test_owner_cannot_open_caisse(self, enterprise):
        c = login(user(enterprise, 'owner'))
        r = c.get(reverse('dashboards:caisse'))
        assert r.status_code == 302
        assert r['Location'] == reverse('dashboards:patron')

    def test_cashier_cannot_open_patron(self, enterprise):
        c = login(user(enterprise, 'cashier'))
        r = c.get(reverse('dashboards:patron'))
        assert r.status_code == 302
        assert r['Location'] == reverse('dashboards:caisse')

    def test_accountant_cannot_open_gerant(self, enterprise):
        c = login(user(enterprise, 'accountant'))
        r = c.get(reverse('dashboards:gerant'))
        assert r.status_code == 302
        assert r['Location'] == reverse('dashboards:comptable')


# ---------------------------------------------------------------------------
# Sidebar grouping is filtered by role
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSidebarGroups:

    def _nav(self, body):
        import re
        m = re.search(r'<nav class="nav-scroll.*?</nav>', body, re.S)
        return m.group(0) if m else ''

    def test_owner_sees_all_groups(self, enterprise):
        c = login(user(enterprise, 'owner'))
        nav = self._nav(c.get(reverse('dashboards:patron')).content.decode())
        for g in ['Tableau de bord', 'Stock', 'Caisse', 'Rapports',
                  'Dépenses', 'Utilisateurs', 'Configuration']:
            assert '>' + g + '<' in nav, f"owner should see group {g}"

    def test_cashier_groups_are_limited(self, enterprise):
        c = login(user(enterprise, 'cashier'))
        nav = self._nav(c.get(reverse('dashboards:caisse')).content.decode())
        assert '>Caisse<' in nav
        assert 'Point de vente' in nav
        # Stock / Rapports / Utilisateurs groups must not appear
        assert '>Stock<' not in nav
        assert '>Rapports<' not in nav
        assert '>Utilisateurs<' not in nav
        assert '>Produits<' not in nav

    def test_collapse_toggle_present(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        assert 'Réduire le menu' in body
        assert 'sidebarCollapsed' in body


@pytest.mark.django_db
class TestDashboardInteractivity:
    """The scaffolding that makes charts/cards drillable (no seeded data needed)."""

    def test_patron_chart_and_links(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        assert 'id="ca-periods"' in body          # chart-bar -> period drill-down
        assert 'id="sales-base"' in body
        assert reverse('stock:out_of_stock') in body  # Rupture card links to out-of-stock
        assert 'onClick' in body

    def test_comptable_chart_bases(self, enterprise):
        c = login(user(enterprise, 'accountant'))
        body = c.get(reverse('dashboards:comptable')).content.decode()
        assert 'id="re-periods"' in body
        assert 'id="expenses-base"' in body
        assert 'id="sales-base"' in body

    def test_caisse_chart_base(self, enterprise, boutique):
        c = login(user(enterprise, 'cashier', location=boutique))
        body = c.get(reverse('dashboards:caisse')).content.decode()
        assert 'id="my-sales-base"' in body

    def test_kpi_cards_are_links(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        # KPI cards drill down: at least the sales-filtered + credits links render
        assert reverse('customers:credit_list') in body
        assert reverse('reports:dashboard') in body
