"""
Unit tests for all models
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.products.models import Product
from apps.stock.models import Stock, StockMovement
from apps.customers.models import Customer, CustomerCredit
from apps.pos.models import Sale, SaleItem
from tests.factories import *


@pytest.mark.django_db
class TestUserModel:
    """Tests for User model"""
    
    # Vérifie que un utilisateur créé est actif et n'est pas membre du staff.
    # Liens : modèle User, apps/accounts/models.py
    def test_create_user(self, user_factory):
        user = user_factory(username='testuser')
        assert user.username == 'testuser'
        assert user.is_active
        assert not user.is_staff
    
    # Vérifie que get_full_name() renvoie le prénom suivi du nom.
    # Liens : modèle User, apps/accounts/models.py
    def test_user_full_name(self, user_factory):
        user = user_factory(first_name='Jean', last_name='Dupont')
        assert user.get_full_name() == 'Jean Dupont'
    
    # Vérifie que un utilisateur peut être créé avec chacun des cinq rôles testés.
    # Liens : modèle User, apps/accounts/models.py
    def test_user_roles(self):
        roles = ['admin', 'manager', 'cashier', 'stock_manager', 'accountant']
        for role in roles:
            user = UserFactory(role=role)
            assert user.role == role


@pytest.mark.django_db
class TestProductModel:
    """Tests for Product model"""
    
    # Vérifie que un produit créé garde son nom et sa catégorie, et il est actif.
    # Liens : modèle Product, apps/products/models.py
    def test_create_product(self, product_factory, category_factory):
        category = category_factory(name='Boissons')
        product = product_factory(name='Coca Cola', category=category)
        assert product.name == 'Coca Cola'
        assert product.category.name == 'Boissons'
        assert product.is_active
    
    # Vérifie que profit_margin vaut 50 % pour un achat à 1000 et une vente à 1500.
    # Liens : Product.profit_margin, apps/products/models.py
    def test_profit_margin(self, product_factory):
        product = product_factory(
            purchase_price=Decimal('1000.00'),
            sale_price=Decimal('1500.00')
        )
        assert product.profit_margin == Decimal('50.00')
    
    # Vérifie que la représentation texte du produit contient son nom.
    # Liens : Product.__str__, apps/products/models.py
    def test_product_str(self, product_factory):
        product = product_factory(name='Test Product')
        assert 'Test Product' in str(product)


@pytest.mark.django_db
class TestStockModel:
    """Tests for Stock model"""
    
    # Vérifie que une ligne de stock garde sa quantité et son produit.
    # Liens : modèle Stock, apps/stock/models.py
    def test_create_stock(self, stock_factory, product_factory):
        product = product_factory()
        stock = stock_factory(product=product, quantity=Decimal('100.00'))
        assert stock.quantity == Decimal('100.00')
        assert stock.product == product
    
    # Vérifie que is_low_stock est vrai quand la quantité est sous le seuil minimum.
    # Liens : Stock.is_low_stock, apps/stock/models.py
    def test_is_low_stock(self, product_factory, stock_factory):
        product = product_factory(min_stock_threshold=10)
        stock = stock_factory(product=product, quantity=Decimal('5.00'))
        assert stock.is_low_stock
    
    # Vérifie que is_low_stock est faux quand la quantité dépasse le seuil minimum.
    # Liens : Stock.is_low_stock, apps/stock/models.py
    def test_is_not_low_stock(self, product_factory, stock_factory):
        product = product_factory(min_stock_threshold=10)
        stock = stock_factory(product=product, quantity=Decimal('20.00'))
        assert not stock.is_low_stock


@pytest.mark.django_db
class TestStockMovementModel:
    """Tests for StockMovement model"""
    
    # Vérifie que un mouvement d'entrée de 50 fait passer le stock de 0 à 50.
    # Liens : StockMovement.save(), apps/stock/models.py
    def test_create_entry_movement(self, product_factory, user_factory):
        product = product_factory()
        user = user_factory()
        stock = StockFactory(product=product, quantity=Decimal('0.00'))
        
        movement = StockMovementFactory(
            product=product,
            user=user,
            movement_type='entry',
            reason='purchase',
            quantity=Decimal('50.00')
        )
        
        stock.refresh_from_db()
        assert movement.movement_type == 'entry'
        assert stock.quantity == Decimal('50.00')
    
    # Vérifie que un mouvement de sortie de 20 fait passer le stock de 100 à 80.
    # Liens : StockMovement.save(), apps/stock/models.py
    def test_create_exit_movement(self, product_factory, user_factory):
        product = product_factory()
        user = user_factory()
        stock = StockFactory(product=product, quantity=Decimal('100.00'))
        
        movement = StockMovementFactory(
            product=product,
            user=user,
            movement_type='exit',
            reason='sale',
            quantity=Decimal('20.00')
        )
        
        stock.refresh_from_db()
        assert movement.movement_type == 'exit'
        assert stock.quantity == Decimal('80.00')


@pytest.mark.django_db
class TestCustomerModel:
    """Tests for Customer model"""
    
    # Vérifie que un client créé est actif et son solde courant vaut zéro.
    # Liens : modèle Customer, apps/customers/models.py
    def test_create_customer(self, customer_factory):
        customer = customer_factory(name='Jean Dupont')
        assert customer.name == 'Jean Dupont'
        assert customer.is_active
        assert customer.current_balance == Decimal('0.00')
    
    # Vérifie que has_outstanding_credit est vrai quand le solde courant est positif.
    # Liens : Customer.has_outstanding_credit, apps/customers/models.py
    def test_has_outstanding_credit(self, customer_factory):
        customer = customer_factory(current_balance=Decimal('5000.00'))
        assert customer.has_outstanding_credit
    
    # Vérifie que has_outstanding_credit est faux quand le solde courant vaut zéro.
    # Liens : Customer.has_outstanding_credit, apps/customers/models.py
    def test_no_outstanding_credit(self, customer_factory):
        customer = customer_factory(current_balance=Decimal('0.00'))
        assert not customer.has_outstanding_credit


@pytest.mark.django_db
class TestSaleModel:
    """Tests for Sale model"""
    
    # Vérifie que une vente garde son client et son vendeur, avec le statut 'completed'.
    # Liens : modèle Sale, apps/pos/models.py
    def test_create_sale(self, sale_factory, customer_factory, user_factory):
        customer = customer_factory()
        user = user_factory(role='cashier')
        sale = sale_factory(
            customer=customer,
            user=user,
            total_amount=Decimal('10000.00'),
            amount_paid=Decimal('10000.00'),
            payment_method='cash'
        )
        assert sale.customer == customer
        assert sale.user == user
        assert sale.status == 'completed'
    
    # Vérifie que le numéro donné par SaleFactory commence par VNT- et dépasse 10 caractères.
    # Liens : SaleFactory de tests/factories.py, modèle Sale, apps/pos/models.py
    def test_sale_number_generation(self):
        sale = SaleFactory()
        assert sale.sale_number.startswith('VNT-')
        assert len(sale.sale_number) > 10
    
    # Vérifie que la monnaie calculée dans le test (500) est conservée après save().
    # Liens : modèle Sale, apps/pos/models.py
    def test_change_calculation(self, sale_factory):
        sale = sale_factory(
            total_amount=Decimal('9500.00'),
            amount_paid=Decimal('10000.00')
        )
        sale.change_amount = sale.amount_paid - sale.total_amount
        sale.save()
        assert sale.change_amount == Decimal('500.00')


@pytest.mark.django_db
class TestSaleItemModel:
    """Tests for SaleItem model"""
    
    # Vérifie que une ligne de 5 articles à 1000 a un total de 5000 (calcul de SaleItemFactory).
    # Liens : SaleItemFactory de tests/factories.py, modèle SaleItem, apps/pos/models.py
    def test_create_sale_item(self, sale_factory, product_factory):
        sale = sale_factory()
        product = product_factory(sale_price=Decimal('1000.00'))
        
        item = SaleItemFactory(
            sale=sale,
            product=product,
            quantity=Decimal('5.00'),
            unit_price=product.sale_price
        )
        
        assert item.total_price == Decimal('5000.00')
    
    # Vérifie que profit vaut (prix de vente - prix d'achat) x quantité.
    # Liens : SaleItem.profit, apps/pos/models.py
    def test_profit_calculation(self, sale_factory, product_factory):
        sale = sale_factory()
        product = product_factory(
            purchase_price=Decimal('800.00'),
            sale_price=Decimal('1000.00')
        )
        
        item = SaleItemFactory(
            sale=sale,
            product=product,
            quantity=Decimal('10.00'),
            unit_price=product.sale_price,
            purchase_price=product.purchase_price
        )
        
        expected_profit = (Decimal('1000.00') - Decimal('800.00')) * Decimal('10.00')
        assert item.profit == expected_profit

