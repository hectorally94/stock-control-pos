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


# Prépare une entreprise de test pour les tableaux de bord.
# Liens : modèle Enterprise (apps/core/models.py)
@pytest.fixture
def enterprise(db):
    return Enterprise.objects.create(name='Dash Test', code='DASHT', currency='FB')


# Prépare une boutique rattachée à l'entreprise de test.
# Liens : modèle Location (apps/locations/models.py)
@pytest.fixture
def boutique(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Boutique Centre', code='BC001',
        location_type='boutique',
    )


# Prépare un utilisateur avec le rôle demandé et, si fourni, un emplacement.
# Liens : UserFactory (tests/factories.py)
def user(enterprise, role, location=None):
    return UserFactory(role=role, enterprise=enterprise, location=location)


# Prépare un client de test déjà connecté avec l'utilisateur donné.
# Liens : django.test.Client, force_login
def login(u):
    c = Client()
    c.force_login(u)
    return c


# ---------------------------------------------------------------------------
# Home dispatch
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHomeDispatch:

    # Vérifie que l'accueil redirige (302) chaque rôle vers son tableau de bord.
    # Liens : home, home_dashboard (apps/core/dashboard_views.py), dashboards:*
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

    # Vérifie que les rôles de stock sont redirigés (302) vers le tableau de bord du stock.
    # Liens : home, home_dashboard (apps/core/dashboard_views.py), stock:dashboard
    @pytest.mark.parametrize('role', ['warehouse_manager', 'stock_manager'])
    def test_stock_roles_land_on_stock_dashboard(self, enterprise, role):
        c = login(user(enterprise, role))
        r = c.get(reverse('home'))
        assert r.status_code == 302
        assert r['Location'] == reverse('stock:dashboard')

    # Vérifie qu'un utilisateur sans entreprise reçoit l'accueil en 200, sans redirection.
    # Liens : home, home_dashboard (apps/core/dashboard_views.py)
    def test_user_without_enterprise_gets_landing(self, db):
        c = login(UserFactory(role='admin'))  # no enterprise
        r = c.get(reverse('home'))
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Each dashboard renders for its role
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDashboardsRender:

    # Vérifie que le propriétaire ouvre le tableau de bord Patron (200, titre présent).
    # Liens : dashboards:patron, patron_dashboard (apps/core/dashboard_views.py)
    def test_patron(self, enterprise):
        c = login(user(enterprise, 'owner'))
        r = c.get(reverse('dashboards:patron'))
        assert r.status_code == 200
        assert 'Patron' in r.content.decode()

    # Vérifie qu'un gérant de boutique ouvre le tableau de bord Gérant (200, titre présent).
    # Liens : dashboards:gerant, gerant_dashboard (apps/core/dashboard_views.py)
    def test_gerant(self, enterprise, boutique):
        c = login(user(enterprise, 'boutique_manager', location=boutique))
        r = c.get(reverse('dashboards:gerant'))
        assert r.status_code == 200
        assert 'Gérant' in r.content.decode()

    # Vérifie qu'un caissier ouvre le tableau de bord Caisse (200, texte « Ma journée »).
    # Liens : dashboards:caisse, caisse_dashboard (apps/core/dashboard_views.py)
    def test_caisse(self, enterprise, boutique):
        c = login(user(enterprise, 'cashier', location=boutique))
        r = c.get(reverse('dashboards:caisse'))
        assert r.status_code == 200
        assert 'Ma journée' in r.content.decode()

    # Vérifie qu'un comptable ouvre le tableau de bord Comptabilité (200, titre présent).
    # Liens : dashboards:comptable, comptable_dashboard (apps/core/dashboard_views.py)
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

    # Vérifie que le propriétaire est renvoyé de Caisse vers son tableau de bord Patron.
    # Liens : dashboards:caisse, dashboards:patron (apps/core/dashboard_views.py)
    def test_owner_cannot_open_caisse(self, enterprise):
        c = login(user(enterprise, 'owner'))
        r = c.get(reverse('dashboards:caisse'))
        assert r.status_code == 302
        assert r['Location'] == reverse('dashboards:patron')

    # Vérifie que le caissier est renvoyé de Patron vers son tableau de bord Caisse.
    # Liens : dashboards:patron, dashboards:caisse (apps/core/dashboard_views.py)
    def test_cashier_cannot_open_patron(self, enterprise):
        c = login(user(enterprise, 'cashier'))
        r = c.get(reverse('dashboards:patron'))
        assert r.status_code == 302
        assert r['Location'] == reverse('dashboards:caisse')

    # Vérifie que le comptable est renvoyé de Gérant vers son tableau de bord Comptabilité.
    # Liens : dashboards:gerant, dashboards:comptable (apps/core/dashboard_views.py)
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

    # Prépare l'extraction du bloc nav de la barre latérale à partir du HTML (chaîne vide si absent).
    # Liens : templates/base.html
    def _nav(self, body):
        import re
        m = re.search(r'<nav class="nav-scroll.*?</nav>', body, re.S)
        return m.group(0) if m else ''

    # Vérifie que le propriétaire voit tous les groupes de la barre latérale.
    # Liens : templates/base.html, dashboards:patron (apps/core/dashboard_views.py)
    def test_owner_sees_all_groups(self, enterprise):
        c = login(user(enterprise, 'owner'))
        nav = self._nav(c.get(reverse('dashboards:patron')).content.decode())
        for g in ['Tableau de bord', 'Stock', 'Caisse', 'Rapports',
                  'Dépenses', 'Utilisateurs', 'Configuration']:
            assert '>' + g + '<' in nav, f"owner should see group {g}"

    # Vérifie que le caissier voit Caisse mais pas les groupes Stock, Rapports, Utilisateurs, Produits.
    # Liens : templates/base.html, dashboards:caisse (apps/core/dashboard_views.py)
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

    # Vérifie que la page contient le bouton « Réduire le menu » et l'état sidebarCollapsed.
    # Liens : templates/base.html, dashboards:patron (apps/core/dashboard_views.py)
    def test_collapse_toggle_present(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        assert 'Réduire le menu' in body
        assert 'sidebarCollapsed' in body


@pytest.mark.django_db
class TestDashboardInteractivity:
    """The scaffolding that makes charts/cards drillable (no seeded data needed)."""

    # Vérifie que Patron contient les données des graphiques, onClick et le lien vers les ruptures.
    # Liens : dashboards:patron (apps/core/dashboard_views.py), stock:out_of_stock
    def test_patron_chart_and_links(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        assert 'id="ca-periods"' in body          # chart-bar -> period drill-down
        assert 'id="sales-base"' in body
        assert reverse('stock:out_of_stock') in body  # Rupture card links to out-of-stock
        assert 'onClick' in body

    # Vérifie que Comptabilité contient les éléments re-periods, expenses-base et sales-base.
    # Liens : dashboards:comptable (apps/core/dashboard_views.py)
    def test_comptable_chart_bases(self, enterprise):
        c = login(user(enterprise, 'accountant'))
        body = c.get(reverse('dashboards:comptable')).content.decode()
        assert 'id="re-periods"' in body
        assert 'id="expenses-base"' in body
        assert 'id="sales-base"' in body

    # Vérifie que Caisse contient l'élément my-sales-base utilisé par le graphique.
    # Liens : dashboards:caisse (apps/core/dashboard_views.py)
    def test_caisse_chart_base(self, enterprise, boutique):
        c = login(user(enterprise, 'cashier', location=boutique))
        body = c.get(reverse('dashboards:caisse')).content.decode()
        assert 'id="my-sales-base"' in body

    # Vérifie que Patron contient les liens des cartes vers les crédits et les rapports.
    # Liens : dashboards:patron (apps/core/dashboard_views.py), customers:credit_list, reports:dashboard
    def test_kpi_cards_are_links(self, enterprise):
        c = login(user(enterprise, 'owner'))
        body = c.get(reverse('dashboards:patron')).content.decode()
        # KPI cards drill down: at least the sales-filtered + credits links render
        assert reverse('customers:credit_list') in body
        assert reverse('reports:dashboard') in body
