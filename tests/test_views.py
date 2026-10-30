"""
Frontend view tests
"""
import pytest
from django.urls import reverse
from django.test import Client

from tests.factories import *


@pytest.mark.django_db
class TestPOSViews:
    """Tests for POS frontend views"""
    
    # Vérifie qu'un visiteur non connecté est redirigé (302) depuis la caisse.
    # Liens : pos:cashier (apps/pos/views_frontend.py)
    def test_cashier_view_requires_login(self):
        client = Client()
        url = reverse('pos:cashier')
        response = client.get(url)
        
        assert response.status_code == 302  # Redirect to login
    
    # Vérifie qu'un caissier ouvre la caisse (200) avec popular_products et categories dans le contexte.
    # Liens : pos:cashier (apps/pos/views_frontend.py)
    def test_cashier_view_accessible_by_cashier(self, cashier_user):
        client = Client()
        client.force_login(cashier_user)
        
        url = reverse('pos:cashier')
        response = client.get(url)
        
        assert response.status_code == 200
        # The cashier POS view exposes popular products + categories; the full
        # product list is loaded on demand via the search_products endpoint.
        assert 'popular_products' in response.context
        assert 'categories' in response.context
    
    # Vérifie qu'une vente envoyée en JSON par un caissier renvoie 200 et success vrai.
    # Liens : pos:create_sale (apps/pos/views_frontend.py)
    def test_create_sale_view(self, cashier_user, customer_factory, product_factory):
        client = Client()
        client.force_login(cashier_user)
        
        customer = customer_factory()
        product = product_factory(sale_price=Decimal('1000.00'))
        StockFactory(product=product, quantity=Decimal('100.00'))
        
        url = reverse('pos:create_sale')
        data = {
            'customer': customer.id,
            'payment_method': 'cash',
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 5,
                    'unit_price': float(product.sale_price),
                    'total_price': 5000.00
                }
            ]
        }
        
        import json
        response = client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data['success']


@pytest.mark.django_db
class TestStockViews:
    """Tests for stock management views"""
    
    # Vérifie qu'un caissier est redirigé (302) depuis le tableau de bord du stock.
    # Liens : stock:dashboard (apps/stock/views_frontend.py)
    def test_dashboard_requires_stock_manager(self, cashier_user):
        client = Client()
        client.force_login(cashier_user)
        
        url = reverse('stock:dashboard')
        response = client.get(url)
        
        assert response.status_code == 302  # Redirected
    
    # Vérifie qu'un gestionnaire ouvre le tableau de bord du stock (200) avec total_products dans le contexte.
    # Liens : stock:dashboard (apps/stock/views_frontend.py)
    def test_dashboard_accessible_by_stock_manager(self, stock_manager_user):
        client = Client()
        client.force_login(stock_manager_user)
        
        url = reverse('stock:dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'total_products' in response.context


@pytest.mark.django_db
class TestReportsViews:
    """Tests for reports views"""
    
    # Vérifie qu'un caissier est redirigé (302) depuis le tableau de bord des rapports.
    # Liens : reports:dashboard (apps/reports/views.py)
    def test_dashboard_requires_manager(self, cashier_user):
        client = Client()
        client.force_login(cashier_user)
        
        url = reverse('reports:dashboard')
        response = client.get(url)
        
        assert response.status_code == 302
    
    # Vérifie qu'un manager ouvre le tableau de bord des rapports avec un statut 200.
    # Liens : reports:dashboard (apps/reports/views.py)
    def test_dashboard_accessible_by_manager(self, manager_user):
        client = Client()
        client.force_login(manager_user)
        
        url = reverse('reports:dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
    
    # Vérifie que l'export des ventes renvoie 200 avec le type de contenu d'un fichier Excel.
    # Liens : reports:export_sales, export_sales_report (apps/reports/views.py)
    def test_export_sales_report(self, manager_user):
        client = Client()
        client.force_login(manager_user)
        
        url = reverse('reports:export_sales')
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

