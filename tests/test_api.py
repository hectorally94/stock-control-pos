"""
API endpoint tests
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from tests.factories import *


@pytest.mark.django_db
class TestAuthAPI:
    """Tests for authentication endpoints"""
    
    # Vérifie qu'un login valide renvoie 200 avec les jetons access et refresh.
    # Liens : POST /api/v1/auth/login/ (token_obtain_pair), api/v1/auth/views.py
    def test_login(self, api_client, user_factory):
        user = user_factory(username='testuser')
        user.set_password('password123')
        user.save()
        
        url = reverse('token_obtain_pair')
        data = {'username': 'testuser', 'password': 'password123'}
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    # Vérifie qu'un login avec de mauvais identifiants renvoie 401.
    # Liens : POST /api/v1/auth/login/ (token_obtain_pair), api/v1/auth/views.py
    def test_login_invalid_credentials(self, api_client):
        url = reverse('token_obtain_pair')
        data = {'username': 'invalid', 'password': 'wrong'}
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProductAPI:
    """Tests for product endpoints"""
    
    # Vérifie que la liste des produits renvoie 200 et les 5 produits créés.
    # Liens : GET product-list, ProductViewSet (api/v1/views/products.py)
    def test_list_products(self, authenticated_client, product_factory):
        ProductFactory.create_batch(5)
        
        url = reverse('product-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    # Vérifie qu'un admin crée un produit : réponse 201 avec le bon nom.
    # Liens : POST product-list, ProductViewSet (api/v1/views/products.py)
    def test_create_product(self, admin_client, category_factory):
        category = category_factory()
        
        url = reverse('product-list')
        data = {
            'category': category.id,
            'name': 'New Product',
            'purchase_price': '1000.00',
            'sale_price': '1500.00',
            'unit': 'piece',
            'min_stock_threshold': 10
        }
        response = admin_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Product'
    
    # Vérifie qu'un admin modifie le nom d'un produit par PATCH : réponse 200 avec le nouveau nom.
    # Liens : PATCH product-detail, ProductViewSet (api/v1/views/products.py)
    def test_update_product(self, admin_client, product_factory):
        product = product_factory()
        
        url = reverse('product-detail', args=[product.id])
        data = {'name': 'Updated Product'}
        response = admin_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Product'
    
    # Vérifie qu'un admin supprime un produit via l'API : réponse 204.
    # Liens : DELETE product-detail, ProductViewSet (api/v1/views/products.py)
    def test_delete_product(self, admin_client, product_factory):
        product = product_factory()
        
        url = reverse('product-detail', args=[product.id])
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestStockAPI:
    """Tests for stock endpoints"""
    
    # Vérifie que le gestionnaire de stock liste les stocks : réponse 200 et 5 lignes.
    # Liens : GET stock-list, StockViewSet (api/v1/views/stock.py)
    def test_list_stock(self, stock_manager_client, stock_factory):
        StockFactory.create_batch(5)
        
        url = reverse('stock-list')
        response = stock_manager_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    # Vérifie qu'une entrée de 50 renvoie 201 et fait passer le stock du produit à 50.
    # Liens : POST stockmovement-list (api/v1/views/stock.py), StockMovement.save() (apps/stock/models.py)
    def test_create_stock_movement(self, stock_manager_client, product_factory, stock_manager_user):
        product = product_factory()
        stock = StockFactory(product=product, quantity=Decimal('0.00'))
        
        url = reverse('stockmovement-list')
        data = {
            'product': product.id,
            'movement_type': 'entry',
            'reason': 'purchase',
            'quantity': '50.00',
            'unit_cost': '1000.00',
            'reference': 'PO-001'
        }
        response = stock_manager_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        stock.refresh_from_db()
        assert stock.quantity == Decimal('50.00')


@pytest.mark.django_db
class TestCustomerAPI:
    """Tests for customer endpoints"""
    
    # Vérifie que le manager liste les clients : réponse 200 et 5 clients.
    # Liens : GET customer-list, CustomerViewSet (api/v1/views/customers.py)
    def test_list_customers(self, manager_client, customer_factory):
        CustomerFactory.create_batch(5)
        
        url = reverse('customer-list')
        response = manager_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    # Vérifie que le manager crée un client : réponse 201 avec le bon nom.
    # Liens : POST customer-list, CustomerViewSet (api/v1/views/customers.py)
    def test_create_customer(self, manager_client):
        url = reverse('customer-list')
        data = {
            'name': 'Jean Dupont',
            'phone': '+221 77 123 45 67',
            'email': 'jean@example.com',
            'credit_limit': '100000.00'
        }
        response = manager_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Jean Dupont'
    
    # Vérifie qu'un caissier peut lire la liste des clients : réponse 200.
    # Liens : GET customer-list, CustomerViewSet (api/v1/views/customers.py)
    def test_cashier_can_read_customers(self, cashier_client, customer_factory):
        CustomerFactory.create_batch(3)
        
        url = reverse('customer-list')
        response = cashier_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSaleAPI:
    """Tests for sale endpoints"""
    
    # Vérifie qu'un caissier liste les ventes : réponse 200 et 5 ventes.
    # Liens : GET sale-list, SaleViewSet (api/v1/views/pos.py)
    def test_list_sales(self, cashier_client, sale_factory):
        SaleFactory.create_batch(5)
        
        url = reverse('sale-list')
        response = cashier_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    # Vérifie qu'un caissier crée une vente : réponse 201 contenant sale_number.
    # Liens : POST sale-list, SaleViewSet (api/v1/views/pos.py)
    def test_create_sale(self, cashier_client, customer_factory, product_factory, cashier_user):
        customer = customer_factory()
        product = product_factory(sale_price=Decimal('1000.00'))
        StockFactory(product=product, quantity=Decimal('100.00'))
        
        url = reverse('sale-list')
        data = {
            'customer': customer.id,
            'payment_method': 'cash',
            'items': [
                {
                    'product': product.id,
                    'quantity': '5.00'
                }
            ]
        }
        response = cashier_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'sale_number' in response.data
    
    # Vérifie que le résumé du jour renvoie 200 avec total_sales et count.
    # Liens : GET sale-today-summary, action today_summary (api/v1/views/pos.py)
    def test_today_summary(self, cashier_client, sale_factory):
        SaleFactory.create_batch(3, status='completed')
        
        url = reverse('sale-today-summary')
        response = cashier_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total_sales' in response.data
        assert 'count' in response.data


@pytest.mark.django_db
class TestExpenseAPI:
    """Tests for expense endpoints"""
    
    # Vérifie que le manager liste les dépenses : réponse 200 et 5 dépenses.
    # Liens : GET expense-list, ExpenseViewSet (api/v1/views/accounting.py)
    def test_list_expenses(self, manager_client, expense_factory):
        ExpenseFactory.create_batch(5)
        
        url = reverse('expense-list')
        response = manager_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
    
    # Vérifie que le manager crée une dépense : réponse 201 avec la bonne description.
    # Liens : POST expense-list, ExpenseViewSet (api/v1/views/accounting.py)
    def test_create_expense(self, manager_client, manager_user):
        category = ExpenseCategoryFactory()
        
        url = reverse('expense-list')
        data = {
            'expense_category': category.id,
            'description': 'Test Expense',
            'amount': '5000.00',
            'expense_date': '2025-12-04',
            'payment_method': 'cash'
        }
        response = manager_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['description'] == 'Test Expense'


@pytest.mark.django_db
class TestPermissions:
    """Tests for role-based permissions"""
    
    # Vérifie qu'un admin accède à la liste des utilisateurs : réponse 200.
    # Liens : GET user-list, UserViewSet (api/v1/views/accounts.py), api/v1/permissions.py
    def test_admin_can_manage_users(self, admin_client):
        url = reverse('user-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    # Vérifie qu'un caissier est refusé sur la liste des utilisateurs : réponse 403.
    # Liens : GET user-list, UserViewSet (api/v1/views/accounts.py), api/v1/permissions.py
    def test_cashier_cannot_manage_users(self, cashier_client):
        url = reverse('user-list')
        response = cashier_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Vérifie qu'un gestionnaire de stock accède à la liste des stocks : réponse 200.
    # Liens : GET stock-list, StockViewSet (api/v1/views/stock.py), api/v1/permissions.py
    def test_stock_manager_can_manage_stock(self, stock_manager_client):
        url = reverse('stock-list')
        response = stock_manager_client.get(url)
        assert response.status_code == status.HTTP_200_OK
    
    # Vérifie qu'un caissier est refusé sur la liste des mouvements de stock : réponse 403.
    # Liens : GET stockmovement-list, StockMovementViewSet (api/v1/views/stock.py), api/v1/permissions.py
    def test_cashier_cannot_manage_stock(self, cashier_client):
        url = reverse('stockmovement-list')
        response = cashier_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

