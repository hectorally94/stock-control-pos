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
    
    def test_cashier_view_requires_login(self):
        client = Client()
        url = reverse('pos:cashier')
        response = client.get(url)
        
        assert response.status_code == 302  # Redirect to login
    
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
    
    def test_dashboard_requires_stock_manager(self, cashier_user):
        client = Client()
        client.force_login(cashier_user)
        
        url = reverse('stock:dashboard')
        response = client.get(url)
        
        assert response.status_code == 302  # Redirected
    
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
    
    def test_dashboard_requires_manager(self, cashier_user):
        client = Client()
        client.force_login(cashier_user)
        
        url = reverse('reports:dashboard')
        response = client.get(url)
        
        assert response.status_code == 302
    
    def test_dashboard_accessible_by_manager(self, manager_user):
        client = Client()
        client.force_login(manager_user)
        
        url = reverse('reports:dashboard')
        response = client.get(url)
        
        assert response.status_code == 200
    
    def test_export_sales_report(self, manager_user):
        client = Client()
        client.force_login(manager_user)
        
        url = reverse('reports:export_sales')
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

