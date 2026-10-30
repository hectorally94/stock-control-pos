"""
Tests for the "Emplacements" column and location filter on the product list.

Covers:
- The product list shows an "Emplacements" column with the locations holding
  each product (quantity > 0).
- A product with no location stock shows the "Aucun emplacement" placeholder.
- The `?location=<pk>` filter restricts the list to products stocked there.
- The emplacement filter dropdown is rendered when locations exist.
"""
import pytest
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from apps.core.models import Enterprise
from apps.locations.models import Location, LocationStock
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement

from tests.factories import UserFactory


# Prépare une entreprise de test à laquelle rattacher les données.
# Liens : modèle Enterprise (apps/core/models.py)
@pytest.fixture
def enterprise():
    return Enterprise.objects.create(name='Hema Test', code='HEMATEST', currency='FB')


# Prépare un emplacement de type boutique pour l'entreprise.
# Liens : modèle Location (apps/locations/models.py)
@pytest.fixture
def boutique(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Boutique Centre', code='BC001',
        location_type='boutique',
    )


# Prépare le dépôt principal de l'entreprise.
# Liens : modèle Location (apps/locations/models.py)
@pytest.fixture
def warehouse(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Dépôt Principal', code='WH001',
        location_type='warehouse', is_main_warehouse=True,
    )


# Prépare un utilisateur admin rattaché à l'entreprise et au dépôt.
# Liens : UserFactory (tests/factories.py)
@pytest.fixture
def admin_user(enterprise, warehouse):
    return UserFactory(role='admin', enterprise=enterprise, location=warehouse)


# Prépare un client de test déjà connecté avec l'utilisateur donné.
# Liens : django.test.Client, force_login
def login(user):
    client = Client()
    client.force_login(user)
    return client


# Prépare un produit à l'unité dans une catégorie créée ou réutilisée.
# Liens : modèles Category et Product (apps/products/models.py)
def make_product(enterprise, name, category_name='Boissons'):
    category, _ = Category.objects.get_or_create(name=category_name, enterprise=enterprise)
    return Product.objects.create(
        name=name, category=category, unit='piece',
        purchase_price=Decimal('800'), sale_price=Decimal('1000'),
        enterprise=enterprise,
    )


@pytest.mark.django_db
class TestEmplacementsColumn:

    # Vérifie que la colonne Emplacements affiche un badge pour le dépôt et la boutique qui ont le produit.
    # Liens : products:product_list (apps/products/views.py), modèle LocationStock
    def test_column_lists_locations_holding_the_product(self, admin_user, enterprise, warehouse, boutique):
        product = make_product(enterprise, 'Coca 50cl')
        LocationStock.objects.create(location=warehouse, product=product, quantity=Decimal('30'))
        LocationStock.objects.create(location=boutique, product=product, quantity=Decimal('12'))

        client = login(admin_user)
        html = client.get(reverse('products:product_list')).content.decode()

        assert 'Emplacements' in html          # column header
        # Badges carry a `title="<name> : <qty>"` marker unique to the column
        assert 'title="Dépôt Principal :' in html
        assert 'title="Boutique Centre :' in html

    # Vérifie qu'un emplacement à quantité 0 n'a pas de badge alors que le dépôt approvisionné en a un.
    # Liens : products:product_list (apps/products/views.py), modèle LocationStock
    def test_zero_quantity_location_is_not_shown(self, admin_user, enterprise, warehouse, boutique):
        product = make_product(enterprise, 'Fanta 50cl')
        LocationStock.objects.create(location=warehouse, product=product, quantity=Decimal('5'))
        LocationStock.objects.create(location=boutique, product=product, quantity=Decimal('0'))

        client = login(admin_user)
        html = client.get(reverse('products:product_list')).content.decode()

        assert 'title="Dépôt Principal :' in html
        # Boutique has 0 stock -> not listed as an emplacement badge for this product
        # (it still appears in the filter dropdown, hence the badge-specific marker)
        assert 'title="Boutique Centre :' not in html

    # Vérifie qu'un produit sans stock affiche « Aucun emplacement » dans la liste.
    # Liens : products:product_list (apps/products/views.py)
    def test_product_without_stock_shows_placeholder(self, admin_user, enterprise):
        make_product(enterprise, 'Sprite 50cl')
        client = login(admin_user)
        html = client.get(reverse('products:product_list')).content.decode()
        assert 'Aucun emplacement' in html


@pytest.mark.django_db
class TestEmplacementFilter:

    # Vérifie que la liste des produits affiche le filtre location avec le dépôt comme choix.
    # Liens : products:product_list (apps/products/views.py)
    def test_filter_dropdown_rendered(self, admin_user, enterprise, warehouse):
        make_product(enterprise, 'Coca 50cl')
        client = login(admin_user)
        html = client.get(reverse('products:product_list')).content.decode()
        assert 'name="location"' in html
        assert 'Dépôt Principal' in html

    # Vérifie que le code Alpine d'envoi automatique des filtres est présent (recherche et listes).
    # Liens : products:product_list (apps/products/views.py)
    def test_filters_auto_submit_markup_present(self, admin_user, enterprise, warehouse):
        make_product(enterprise, 'Coca 50cl')
        client = login(admin_user)
        html = client.get(reverse('products:product_list')).content.decode()
        # Search box auto-submits (debounced) and dropdowns submit on change
        assert '@input.debounce' in html
        assert '$el.form.requestSubmit()' in html
        assert '@change=' in html

    # Vérifie que ?location= n'affiche que les produits stockés à cet emplacement.
    # Liens : products:product_list (apps/products/views.py), modèle LocationStock
    def test_filter_restricts_to_products_at_location(self, admin_user, enterprise, warehouse, boutique):
        in_boutique = make_product(enterprise, 'In Boutique')
        in_warehouse = make_product(enterprise, 'In Warehouse')
        LocationStock.objects.create(location=boutique, product=in_boutique, quantity=Decimal('10'))
        LocationStock.objects.create(location=warehouse, product=in_warehouse, quantity=Decimal('10'))

        client = login(admin_user)
        html = client.get(reverse('products:product_list') + f'?location={boutique.pk}').content.decode()

        assert 'In Boutique' in html
        assert 'In Warehouse' not in html


@pytest.mark.django_db
class TestProductDetailStock:

    # Vérifie que la fiche produit détaille le stock par emplacement et affiche le total 42.
    # Liens : products:product_detail (apps/products/views.py), modèle Stock
    def test_per_emplacement_breakdown_and_total(self, admin_user, enterprise, warehouse, boutique):
        product = make_product(enterprise, 'Kisinia')
        Stock.objects.create(product=product, location=warehouse, enterprise=enterprise, quantity=Decimal('30'))
        Stock.objects.create(product=product, location=boutique, enterprise=enterprise, quantity=Decimal('12'))

        client = login(admin_user)
        html = client.get(reverse('products:product_detail', args=[product.pk])).content.decode()

        assert 'Stock par emplacement' in html
        assert 'Dépôt Principal' in html
        assert 'Boutique Centre' in html
        assert '42' in html          # total = 30 + 12

    # Vérifie qu'un produit sans stock ni seuil affiche l'état vide, sans alerte de seuil minimum.
    # Liens : products:product_detail (apps/products/views.py)
    def test_no_stock_shows_empty_state_and_no_false_alert(self, admin_user, enterprise):
        # Newly created product, no stock, no threshold -> no "below minimum" alarm
        product = make_product(enterprise, 'Kisinia')
        client = login(admin_user)
        html = client.get(reverse('products:product_detail', args=[product.pk])).content.decode()

        assert 'Aucun stock dans les emplacements' in html
        assert 'en dessous du seuil minimum' not in html

    # Vérifie que l'alerte de seuil s'affiche quand le stock (5) est sous le seuil configuré (20).
    # Liens : products:product_detail (apps/products/views.py), modèle Stock
    def test_alert_only_when_threshold_configured(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise, 'Kisinia')
        product.min_stock_threshold = Decimal('20')
        product.save()
        Stock.objects.create(product=product, location=warehouse, enterprise=enterprise, quantity=Decimal('5'))

        client = login(admin_user)
        html = client.get(reverse('products:product_detail', args=[product.pk])).content.decode()
        assert 'en dessous du seuil minimum' in html


@pytest.mark.django_db
class TestInStockPage:

    # Vérifie que le tableau de bord du stock contient un lien vers la page Produits en Stock.
    # Liens : stock:dashboard, stock:in_stock (apps/stock/views_frontend.py)
    def test_card_links_to_in_stock_page(self, admin_user, enterprise, warehouse):
        from django.urls import reverse as r
        client = login(admin_user)
        html = client.get(r('stock:dashboard')).content.decode()
        assert r('stock:in_stock') in html

    # Vérifie que la page affiche les deux onglets, les deux produits et le total de 526 unités.
    # Liens : stock:in_stock, in_stock_view (apps/stock/views_frontend.py)
    def test_in_stock_shows_both_tabs_with_totals(self, admin_user, enterprise, warehouse, boutique):
        p1 = make_product(enterprise, 'Coca 50cl')
        p2 = make_product(enterprise, 'Fanta 50cl')
        Stock.objects.create(product=p1, location=warehouse, enterprise=enterprise, quantity=Decimal('100'))
        Stock.objects.create(product=p1, location=boutique, enterprise=enterprise, quantity=Decimal('26'))
        Stock.objects.create(product=p2, location=warehouse, enterprise=enterprise, quantity=Decimal('400'))

        client = login(admin_user)
        html = client.get(reverse('stock:in_stock')).content.decode()

        assert 'Par produit' in html
        assert 'Détail des unités' in html
        # 2 distinct products, total units 526
        assert 'Coca 50cl' in html
        assert 'Fanta 50cl' in html
        assert '526' in html        # 100 + 26 + 400

    # Vérifie qu'un produit dont le stock est à 0 n'apparaît pas sur la page Produits en Stock.
    # Liens : stock:in_stock, in_stock_view (apps/stock/views_frontend.py)
    def test_zero_quantity_rows_excluded(self, admin_user, enterprise, warehouse):
        p = make_product(enterprise, 'Empty Product')
        Stock.objects.create(product=p, location=warehouse, enterprise=enterprise, quantity=Decimal('0'))
        client = login(admin_user)
        html = client.get(reverse('stock:in_stock')).content.decode()
        # Product with only 0-qty rows is not "in stock"
        assert 'Empty Product' not in html

    # Vérifie que ?search=Coca garde le produit recherché et retire l'autre.
    # Liens : stock:in_stock, in_stock_view (apps/stock/views_frontend.py)
    def test_in_stock_search_filters_by_product(self, admin_user, enterprise, warehouse):
        keep = make_product(enterprise, 'Coca 50cl')
        drop = make_product(enterprise, 'Fanta 50cl')
        Stock.objects.create(product=keep, location=warehouse, enterprise=enterprise, quantity=Decimal('10'))
        Stock.objects.create(product=drop, location=warehouse, enterprise=enterprise, quantity=Decimal('10'))

        client = login(admin_user)
        html = client.get(reverse('stock:in_stock') + '?search=Coca').content.decode()
        assert 'Coca 50cl' in html
        assert 'Fanta 50cl' not in html

    # Vérifie que ?location= sur l'onglet unités garde la boutique et retire la ligne du dépôt (100).
    # Liens : stock:in_stock, in_stock_view (apps/stock/views_frontend.py)
    def test_in_stock_location_filter(self, admin_user, enterprise, warehouse, boutique):
        p = make_product(enterprise, 'Coca 50cl')
        Stock.objects.create(product=p, location=warehouse, enterprise=enterprise, quantity=Decimal('100'))
        Stock.objects.create(product=p, location=boutique, enterprise=enterprise, quantity=Decimal('5'))

        client = login(admin_user)
        html = client.get(reverse('stock:in_stock') + f'?location={boutique.pk}&tab=units').content.decode()
        # Only the boutique row (qty 5) remains; warehouse 100 filtered out
        assert 'Boutique Centre' in html
        assert '>100<' not in html
        # Filter bar + auto-submit present
        assert '@input.debounce' in html


@pytest.mark.django_db
class TestProductDetailLocationLinks:

    # Vérifie que la ligne d'emplacement de la fiche produit contient un lien vers cet emplacement.
    # Liens : products:product_detail (apps/products/views.py), locations:detail
    def test_emplacement_row_links_to_location_detail(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise, 'Biere Primus 50cl')
        Stock.objects.create(product=product, location=warehouse, enterprise=enterprise, quantity=Decimal('350'))

        client = login(admin_user)
        html = client.get(reverse('products:product_detail', args=[product.pk])).content.decode()
        assert reverse('locations:detail', args=[warehouse.pk]) in html


@pytest.mark.django_db
class TestLocationDetail:

    # Vérifie que la page emplacement liste tous ses produits, même à 0, avec liens et recherche.
    # Liens : locations:detail (apps/locations/views.py), products:product_detail
    def test_full_product_list_clickable(self, admin_user, enterprise, boutique):
        p1 = make_product(enterprise, 'Biere Primus 50cl')
        p2 = make_product(enterprise, 'Biscuits Oreo')
        LocationStock.objects.create(location=boutique, product=p1, quantity=Decimal('5'))
        LocationStock.objects.create(location=boutique, product=p2, quantity=Decimal('0'))

        client = login(admin_user)
        html = client.get(reverse('locations:detail', args=[boutique.pk])).content.decode()

        assert 'Produits dans cet emplacement' in html
        # Both products listed (not just low/out), each linking to its detail page
        assert 'Biere Primus 50cl' in html
        assert 'Biscuits Oreo' in html
        assert reverse('products:product_detail', args=[p1.pk]) in html
        assert reverse('products:product_detail', args=[p2.pk]) in html
        # Search box present
        assert 'Rechercher un produit' in html

    # Vérifie qu'une boutique sans coordonnées affiche quand même son code et Responsable « Non assigné ».
    # Liens : locations:detail (apps/locations/views.py)
    def test_details_card_always_populated(self, admin_user, enterprise, boutique):
        # Boutique has no address/phone/email/manager -> card must still show Type/Code/Responsable
        client = login(admin_user)
        html = client.get(reverse('locations:detail', args=[boutique.pk])).content.decode()
        assert 'BC001' in html            # code
        assert 'Responsable' in html
        assert 'Non assigné' in html

    # Vérifie que le bouton retour reprend le chemin interne donné par ?next=.
    # Liens : locations:detail (apps/locations/views.py)
    def test_back_button_uses_next_param(self, admin_user, enterprise, boutique):
        client = login(admin_user)
        url = reverse('locations:detail', args=[boutique.pk]) + '?next=/products/5/'
        html = client.get(url).content.decode()
        assert 'href="/products/5/"' in html

    # Vérifie que, sans ?next=, la page contient le lien vers le tableau de bord des emplacements.
    # Liens : locations:detail (apps/locations/views.py), locations:dashboard
    def test_back_button_defaults_to_dashboard(self, admin_user, enterprise, boutique):
        client = login(admin_user)
        html = client.get(reverse('locations:detail', args=[boutique.pk])).content.decode()
        assert reverse('locations:dashboard') in html

    # Vérifie qu'une URL externe dans ?next= est ignorée au profit du tableau de bord des emplacements.
    # Liens : locations:detail (apps/locations/views.py), locations:dashboard
    def test_back_button_rejects_external_url(self, admin_user, enterprise, boutique):
        client = login(admin_user)
        url = reverse('locations:detail', args=[boutique.pk]) + '?next=https://evil.com/x'
        html = client.get(url).content.decode()
        assert 'evil.com' not in html
        assert reverse('locations:dashboard') in html

    # Vérifie que la fiche produit contient un paramètre next= pour le lien vers l'emplacement.
    # Liens : products:product_detail (apps/products/views.py)
    def test_product_detail_location_link_carries_next(self, admin_user, enterprise, warehouse):
        product = make_product(enterprise, 'Biere Primus 50cl')
        Stock.objects.create(product=product, location=warehouse, enterprise=enterprise, quantity=Decimal('350'))
        client = login(admin_user)
        html = client.get(reverse('products:product_detail', args=[product.pk])).content.decode()
        # The emplacement link includes ?next= back to this product
        assert 'next=' in html


@pytest.mark.django_db
class TestMovementsHistory:

    # Vérifie que ?product=&location= exclut les mouvements d'un autre emplacement ou d'un autre produit.
    # Liens : stock:movements, movements_view (apps/stock/views_frontend.py)
    def test_filtered_by_product_and_location(self, admin_user, enterprise, warehouse, boutique):
        p = make_product(enterprise, 'Biere Primus 50cl')
        other = make_product(enterprise, 'Autre Produit')
        StockMovement.objects.create(product=p, location=boutique, enterprise=enterprise, user=admin_user,
                                     movement_type='entry', reason='purchase', quantity=Decimal('3'))
        StockMovement.objects.create(product=p, location=warehouse, enterprise=enterprise, user=admin_user,
                                     movement_type='entry', reason='purchase', quantity=Decimal('99'))
        StockMovement.objects.create(product=other, location=boutique, enterprise=enterprise, user=admin_user,
                                     movement_type='entry', reason='purchase', quantity=Decimal('77'))

        client = login(admin_user)
        html = client.get(reverse('stock:movements') + f'?product={p.pk}&location={boutique.pk}').content.decode()

        assert 'Historique' in html
        assert 'Biere Primus 50cl' in html
        # Movement at warehouse (99) and other product (77) are excluded
        assert '+99' not in html
        assert '+77' not in html

    # Vérifie que la page emplacement propose un lien next= et un lien Historique filtré par produit.
    # Liens : locations:detail (apps/locations/views.py), stock:movements
    def test_location_detail_has_history_and_next_links(self, admin_user, enterprise, boutique):
        product = make_product(enterprise, 'Biere Primus 50cl')
        LocationStock.objects.create(location=boutique, product=product, quantity=Decimal('5'))

        client = login(admin_user)
        html = client.get(reverse('locations:detail', args=[boutique.pk])).content.decode()
        # Entrée carries next back to this location; Historique points to movements
        assert 'next=' in html
        assert f'product={product.pk}&location={boutique.pk}' in html
        assert 'Historique' in html
