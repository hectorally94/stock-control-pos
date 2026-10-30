"""
End-to-end tests for ALL input forms in the application.
Tests form submission, validation, and data persistence.
"""
import json
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement
from apps.customers.models import Customer, CustomerCredit, CreditPayment
from apps.pos.models import Sale, SaleItem
from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession
from apps.locations.models import Location, LocationStock
from apps.transfers.models import Transfer, TransferItem
from apps.core.models import Enterprise

from tests.factories import (
    UserFactory, CategoryFactory, ProductFactory, StockFactory,
    CustomerFactory, CustomerCreditFactory, ExpenseCategoryFactory,
    ExpenseFactory, CashRegisterSessionFactory,
)


# ============================================================================
# HELPERS
# ============================================================================

@pytest.fixture
def enterprise():
    """Create an enterprise for testing"""
    return Enterprise.objects.create(
        name='Test Enterprise',
        code='TEST001',
        currency='FB',
    )


@pytest.fixture
def location_warehouse(enterprise):
    """Create a warehouse location"""
    return Location.objects.create(
        enterprise=enterprise,
        name='Dépôt Principal',
        code='WH001',
        location_type='warehouse',
        is_main_warehouse=True,
    )


@pytest.fixture
def location_boutique(enterprise):
    """Create a boutique location"""
    return Location.objects.create(
        enterprise=enterprise,
        name='Boutique Centre',
        code='BT001',
        location_type='boutique',
    )


@pytest.fixture
def admin_user_with_enterprise(enterprise, location_warehouse):
    """Admin user with enterprise and location"""
    user = UserFactory(
        role='admin',
        enterprise=enterprise,
        location=location_warehouse,
    )
    return user


@pytest.fixture
def manager_user_with_enterprise(enterprise, location_warehouse):
    """Manager user with enterprise"""
    return UserFactory(
        role='manager',
        enterprise=enterprise,
        location=location_warehouse,
    )


@pytest.fixture
def cashier_user_with_enterprise(enterprise, location_boutique):
    """Cashier user with enterprise and boutique location"""
    return UserFactory(
        role='cashier',
        enterprise=enterprise,
        location=location_boutique,
    )


@pytest.fixture
def stock_manager_user_with_enterprise(enterprise, location_warehouse):
    """Stock manager with enterprise"""
    return UserFactory(
        role='stock_manager',
        enterprise=enterprise,
        location=location_warehouse,
    )


@pytest.fixture
def accountant_user_with_enterprise(enterprise):
    """Accountant user with enterprise"""
    return UserFactory(
        role='accountant',
        enterprise=enterprise,
    )


def login_client(user):
    """Create a logged-in test client"""
    client = Client()
    client.force_login(user)
    return client


# ============================================================================
# 1. LOGIN FORM
# ============================================================================

@pytest.mark.django_db
class TestLoginForm:
    """Tests for the login form"""

    def test_login_page_loads(self):
        client = Client()
        response = client.get(reverse('login'))
        assert response.status_code == 200

    def test_login_with_valid_credentials(self):
        user = UserFactory(role='admin')
        client = Client()
        response = client.post(reverse('login'), {
            'username': user.username,
            'password': 'password123',
        })
        # Successful login redirects
        assert response.status_code == 302

    def test_login_with_invalid_password(self):
        user = UserFactory(role='admin')
        client = Client()
        response = client.post(reverse('login'), {
            'username': user.username,
            'password': 'wrongpassword',
        })
        # Failed login stays on page
        assert response.status_code == 200

    def test_login_with_nonexistent_user(self):
        client = Client()
        response = client.post(reverse('login'), {
            'username': 'nonexistent',
            'password': 'password123',
        })
        assert response.status_code == 200

    def test_login_with_empty_fields(self):
        client = Client()
        response = client.post(reverse('login'), {
            'username': '',
            'password': '',
        })
        assert response.status_code == 200


# ============================================================================
# 2. USER MANAGEMENT FORMS
# ============================================================================

@pytest.mark.django_db
class TestUserCreateForm:
    """Tests for user creation form"""

    def test_user_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('accounts:user_create'))
        assert response.status_code == 200

    def test_create_user_success(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'newcashier',
            'email': 'newcashier@example.com',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'phone': '+225 01 02 03 04',
            'role': 'cashier',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        assert response.status_code == 302  # Redirect on success
        assert User.objects.filter(username='newcashier').exists()
        new_user = User.objects.get(username='newcashier')
        assert new_user.role == 'cashier'
        assert new_user.enterprise == admin_user_with_enterprise.enterprise

    def test_create_user_missing_username(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': '',
            'email': 'test@example.com',
            'role': 'cashier',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        assert response.status_code == 200  # Re-renders form with errors

    def test_create_user_duplicate_username(self, admin_user_with_enterprise):
        UserFactory(username='existing_user')
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'existing_user',
            'email': 'new@example.com',
            'role': 'cashier',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        assert response.status_code == 200  # Re-renders with errors

    def test_create_user_password_mismatch(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'cashier',
            'password': 'password1',
            'password_confirm': 'password2',
        })
        assert response.status_code == 200

    def test_create_user_short_password(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'role': 'cashier',
            'password': '123',
            'password_confirm': '123',
        })
        assert response.status_code == 200

    def test_create_user_with_location(self, admin_user_with_enterprise, location_boutique):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'boutique_cashier',
            'email': 'boutique@example.com',
            'role': 'cashier',
            'location': location_boutique.pk,
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        assert response.status_code == 302
        new_user = User.objects.get(username='boutique_cashier')
        assert new_user.location == location_boutique

    def test_manager_cannot_create_admin(self, manager_user_with_enterprise):
        client = login_client(manager_user_with_enterprise)
        response = client.post(reverse('accounts:user_create'), {
            'username': 'hackeradmin',
            'email': 'hack@example.com',
            'role': 'admin',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        # Should not create the user or should show error
        assert response.status_code == 200
        assert not User.objects.filter(username='hackeradmin').exists()

    def test_cashier_cannot_access_user_create(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounts:user_create'))
        assert response.status_code == 302  # Redirected away


@pytest.mark.django_db
class TestUserEditForm:
    """Tests for user edit form"""

    def test_edit_user_page_loads(self, admin_user_with_enterprise):
        target = UserFactory(
            role='cashier',
            enterprise=admin_user_with_enterprise.enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('accounts:user_edit', args=[target.pk]))
        assert response.status_code == 200

    def test_edit_user_success(self, admin_user_with_enterprise):
        target = UserFactory(
            role='cashier',
            enterprise=admin_user_with_enterprise.enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_edit', args=[target.pk]), {
            'email': 'updated@example.com',
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'phone': '+225 99 88 77 66',
            'role': 'cashier',
        })
        assert response.status_code == 302
        target.refresh_from_db()
        assert target.email == 'updated@example.com'
        assert target.first_name == 'UpdatedFirst'

    def test_edit_user_change_password(self, admin_user_with_enterprise):
        target = UserFactory(
            role='cashier',
            enterprise=admin_user_with_enterprise.enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_edit', args=[target.pk]), {
            'email': target.email,
            'role': 'cashier',
            'new_password': 'newpassword123',
        })
        assert response.status_code == 302
        target.refresh_from_db()
        assert target.check_password('newpassword123')

    def test_cannot_edit_self(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('accounts:user_edit', args=[admin_user_with_enterprise.pk]))
        assert response.status_code == 302  # Redirected with warning


@pytest.mark.django_db
class TestUserToggleActive:
    """Tests for user toggle active"""

    def test_toggle_user_active(self, admin_user_with_enterprise):
        target = UserFactory(
            role='cashier',
            enterprise=admin_user_with_enterprise.enterprise,
            is_active=True,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounts:user_toggle_active', args=[target.pk]))
        assert response.status_code == 302
        target.refresh_from_db()
        assert target.is_active is False

    def test_cannot_deactivate_self(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(
            reverse('accounts:user_toggle_active', args=[admin_user_with_enterprise.pk])
        )
        assert response.status_code == 302
        admin_user_with_enterprise.refresh_from_db()
        assert admin_user_with_enterprise.is_active is True


# ============================================================================
# 3. PRODUCT CATEGORY FORMS
# ============================================================================

@pytest.mark.django_db
class TestCategoryCreateForm:
    """Tests for category creation"""

    def test_category_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('products:category_create'))
        assert response.status_code == 200

    def test_create_category_success(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_create'), {
            'name': 'Boissons',
            'description': 'Catégorie des boissons',
            'is_active': 'on',
        })
        assert response.status_code == 302
        assert Category.objects.filter(name='Boissons').exists()

    def test_create_category_empty_name(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_create'), {
            'name': '',
            'description': 'Empty name',
        })
        assert response.status_code == 200
        assert Category.objects.count() == 0

    def test_create_category_duplicate_name(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        Category.objects.create(name='Existing', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_create'), {
            'name': 'Existing',
        })
        assert response.status_code == 200
        assert Category.objects.filter(name='Existing').count() == 1


@pytest.mark.django_db
class TestCategoryEditForm:
    """Tests for category editing"""

    def test_edit_category_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(
            name='Old Name', enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_edit', args=[category.pk]), {
            'name': 'New Name',
            'description': 'Updated description',
            'is_active': 'on',
        })
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.name == 'New Name'

    def test_edit_category_deactivate(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(
            name='Test Cat', enterprise=enterprise, is_active=True,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_edit', args=[category.pk]), {
            'name': 'Test Cat',
        })
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.is_active is False


# ============================================================================
# 4. PRODUCT FORMS
# ============================================================================

@pytest.mark.django_db
class TestProductCreateForm:
    """Tests for product creation"""

    def test_product_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('products:product_create'))
        assert response.status_code == 200

    def test_create_product_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Test Cat', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'Coca Cola 1.5L',
            'category': category.pk,
            'unit': 'pièce',
            'purchase_price': '500',
            'sale_price': '750',
            'tax_rate': '0',
            'min_stock_threshold': '10',
            'is_active': 'on',
        })
        assert response.status_code == 302
        product = Product.objects.get(name='Coca Cola 1.5L')
        assert product.purchase_price == 500
        assert product.sale_price == 750
        assert product.category == category
        # Verify initial stock created
        assert Stock.objects.filter(product=product).exists()

    def test_create_product_missing_name(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': '',
            'category': category.pk,
            'purchase_price': '500',
            'sale_price': '750',
        })
        assert response.status_code == 200
        assert Product.objects.count() == 0

    def test_create_product_missing_category(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'Test Product',
            'category': '',
            'purchase_price': '500',
            'sale_price': '750',
        })
        assert response.status_code == 200
        assert Product.objects.count() == 0

    def test_create_product_negative_price(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'Bad Product',
            'category': category.pk,
            'purchase_price': '-100',
            'sale_price': '750',
        })
        assert response.status_code == 200
        assert Product.objects.count() == 0

    def test_create_product_with_barcode(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'Barcode Product',
            'category': category.pk,
            'barcode': '1234567890123',
            'purchase_price': '500',
            'sale_price': '750',
            'is_active': 'on',
        })
        assert response.status_code == 302
        product = Product.objects.get(name='Barcode Product')
        assert product.barcode == '1234567890123'

    def test_create_product_duplicate_barcode(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        Product.objects.create(
            name='Existing', category=category, barcode='DUPE123',
            purchase_price=100, sale_price=200, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'New Product',
            'category': category.pk,
            'barcode': 'DUPE123',
            'purchase_price': '500',
            'sale_price': '750',
        })
        assert response.status_code == 200
        assert Product.objects.filter(barcode='DUPE123').count() == 1

    def test_create_product_invalid_price(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_create'), {
            'name': 'Invalid Price Product',
            'category': category.pk,
            'purchase_price': 'abc',
            'sale_price': '750',
        })
        assert response.status_code == 200
        assert Product.objects.count() == 0


@pytest.mark.django_db
class TestProductEditForm:
    """Tests for product editing"""

    def test_edit_product_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Original', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_edit', args=[product.pk]), {
            'name': 'Updated Name',
            'category': category.pk,
            'unit': 'pièce',
            'purchase_price': '600',
            'sale_price': '900',
            'tax_rate': '0',
            'min_stock_threshold': '5',
            'is_active': 'on',
        })
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.name == 'Updated Name'
        assert product.sale_price == 900

    def test_edit_product_toggle_popular(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Test', category=category,
            purchase_price=500, sale_price=750,
            is_popular=False, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_edit', args=[product.pk]), {
            'name': 'Test',
            'category': category.pk,
            'purchase_price': '500',
            'sale_price': '750',
            'is_popular': 'on',
            'is_active': 'on',
        })
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.is_popular is True


# ============================================================================
# 5. CUSTOMER FORMS
# ============================================================================

@pytest.mark.django_db
class TestCustomerCreateForm:
    """Tests for customer creation"""

    def test_customer_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('customers:customer_create'))
        assert response.status_code == 200

    def test_create_customer_success(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': 'Abdoul Koné',
            'phone': '+225 07 08 09 10',
            'email': 'abdoul@example.com',
            'address': '123 Rue de Abidjan',
            'credit_limit': '50000',
            'notes': 'Client fidèle',
        })
        assert response.status_code == 302
        customer = Customer.objects.get(name='Abdoul Koné')
        assert customer.phone == '+225 07 08 09 10'
        assert customer.credit_limit == Decimal('50000')

    def test_create_customer_name_only(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': 'Simple Customer',
        })
        assert response.status_code == 302
        assert Customer.objects.filter(name='Simple Customer').exists()

    def test_create_customer_missing_name(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': '',
            'phone': '+225 00 00 00 00',
        })
        assert response.status_code == 200
        assert Customer.objects.count() == 0

    def test_create_customer_duplicate_phone(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        Customer.objects.create(
            name='Existing', phone='+225 11 22 33 44',
            enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': 'Another Customer',
            'phone': '+225 11 22 33 44',
        })
        assert response.status_code == 200

    def test_create_customer_negative_credit_limit(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': 'Bad Credit Customer',
            'credit_limit': '-5000',
        })
        assert response.status_code == 200
        assert Customer.objects.count() == 0

    def test_cashier_can_create_customer(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('customers:customer_create'), {
            'name': 'Cashier Created',
        })
        assert response.status_code == 302
        assert Customer.objects.filter(name='Cashier Created').exists()


@pytest.mark.django_db
class TestCustomerEditForm:
    """Tests for customer editing"""

    def test_edit_customer_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        customer = Customer.objects.create(
            name='Original Name', enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_edit', args=[customer.pk]), {
            'name': 'Updated Name',
            'phone': '+225 55 66 77 88',
            'credit_limit': '100000',
            'is_active': 'on',
        })
        assert response.status_code == 302
        customer.refresh_from_db()
        assert customer.name == 'Updated Name'
        assert customer.credit_limit == Decimal('100000')

    def test_edit_customer_deactivate(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        customer = Customer.objects.create(
            name='Active Customer', enterprise=enterprise, is_active=True,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_edit', args=[customer.pk]), {
            'name': 'Active Customer',
            'credit_limit': '0',
            # is_active not set = False
        })
        assert response.status_code == 302
        customer.refresh_from_db()
        assert customer.is_active is False


# ============================================================================
# 6. CREDIT PAYMENT FORM
# ============================================================================

@pytest.mark.django_db
class TestRecordPaymentForm:
    """Tests for recording credit payments"""

    def _create_credit(self, user, enterprise, remaining=Decimal('50000'), status='pending'):
        """Helper to create a customer credit with required sale.
        Uses 'credit' payment method which triggers signal to auto-create CustomerCredit.
        """
        customer = Customer.objects.create(
            name='Debtor', enterprise=enterprise, credit_limit=Decimal('500000'),
        )
        sale = Sale.objects.create(
            sale_number=f'VNT-TEST-{Sale.objects.count() + 1:08d}',
            customer=customer,
            user=user,
            enterprise=enterprise,
            subtotal=Decimal('50000'),
            total_amount=Decimal('50000'),
            amount_paid=Decimal('0'),
            payment_method='credit',
            status='completed',
        )
        # Signal auto-creates the credit, fetch it
        credit = CustomerCredit.objects.get(sale=sale)
        # Adjust remaining and status for test scenarios
        if remaining != credit.remaining_amount or status != credit.status:
            credit.remaining_amount = remaining
            credit.status = status
            credit.due_date = date.today() + timedelta(days=30)
            credit.save()
        return customer, credit

    def test_payment_page_loads(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        _, credit = self._create_credit(admin_user_with_enterprise, enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('customers:record_payment', args=[credit.pk]))
        assert response.status_code == 200

    def test_record_payment_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        _, credit = self._create_credit(admin_user_with_enterprise, enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:record_payment', args=[credit.pk]), {
            'amount': '25000',
            'payment_method': 'cash',
            'payment_reference': 'PAY-001',
            'notes': 'Paiement partiel',
        })
        assert response.status_code == 302
        assert CreditPayment.objects.filter(credit=credit).exists()
        payment = CreditPayment.objects.get(credit=credit)
        assert payment.amount == Decimal('25000')

    def test_record_payment_zero_amount(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        _, credit = self._create_credit(admin_user_with_enterprise, enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:record_payment', args=[credit.pk]), {
            'amount': '0',
            'payment_method': 'cash',
        })
        assert response.status_code == 200
        assert CreditPayment.objects.count() == 0

    def test_record_payment_exceeds_remaining(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        _, credit = self._create_credit(
            admin_user_with_enterprise, enterprise,
            remaining=Decimal('10000'), status='partial',
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:record_payment', args=[credit.pk]), {
            'amount': '20000',
            'payment_method': 'cash',
        })
        assert response.status_code == 200
        assert CreditPayment.objects.count() == 0

    def test_record_payment_already_paid(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        _, credit = self._create_credit(
            admin_user_with_enterprise, enterprise,
            remaining=Decimal('0'), status='paid',
        )
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('customers:record_payment', args=[credit.pk]))
        assert response.status_code == 302  # Redirected (already paid)


# ============================================================================
# 7. POS FORMS (AJAX/JSON)
# ============================================================================

@pytest.mark.django_db
class TestPOSCreateSaleForm:
    """Tests for POS sale creation (AJAX)"""

    def test_cashier_view_loads(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('pos:cashier'))
        assert response.status_code == 200

    def test_create_sale_success(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        category = Category.objects.create(name='Drinks', enterprise=enterprise)
        product = Product.objects.create(
            name='Fanta', category=category,
            purchase_price=300, sale_price=500, enterprise=enterprise,
        )
        Stock.objects.create(product=product, quantity=100, enterprise=enterprise)
        customer = Customer.objects.create(name='Client Test', enterprise=enterprise)

        client = login_client(cashier_user_with_enterprise)
        data = {
            'customer_id': customer.pk,
            'subtotal': 2500,
            'discount_amount': 0,
            'discount_percent': 0,
            'tax_amount': 0,
            'total_amount': 2500,
            'amount_paid': 3000,
            'change_amount': 500,
            'payment_method': 'cash',
            'items': [
                {
                    'product_id': product.pk,
                    'quantity': 5,
                    'unit_price': 500,
                    'total_price': 2500,
                }
            ]
        }
        response = client.post(
            reverse('pos:create_sale'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert Sale.objects.count() == 1
        sale = Sale.objects.first()
        assert sale.total_amount == Decimal('2500')
        assert SaleItem.objects.filter(sale=sale).count() == 1

    def test_create_sale_no_items(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        data = {
            'subtotal': 0,
            'total_amount': 0,
            'amount_paid': 0,
            'change_amount': 0,
            'payment_method': 'cash',
            'items': [],
        }
        response = client.post(
            reverse('pos:create_sale'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 200
        # Sale may be created with no items (this is a known behavior)

    def test_create_sale_invalid_product(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        data = {
            'subtotal': 500,
            'total_amount': 500,
            'amount_paid': 500,
            'change_amount': 0,
            'payment_method': 'cash',
            'items': [
                {
                    'product_id': 99999,
                    'quantity': 1,
                    'unit_price': 500,
                    'total_price': 500,
                }
            ]
        }
        response = client.post(
            reverse('pos:create_sale'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_create_sale_credit_payment(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        category = Category.objects.create(name='Food', enterprise=enterprise)
        product = Product.objects.create(
            name='Rice 5kg', category=category,
            purchase_price=2000, sale_price=3000, enterprise=enterprise,
        )
        Stock.objects.create(product=product, quantity=50, enterprise=enterprise)
        customer = Customer.objects.create(
            name='Credit Customer', enterprise=enterprise,
            credit_limit=100000,
        )

        client = login_client(cashier_user_with_enterprise)
        data = {
            'customer_id': customer.pk,
            'subtotal': 3000,
            'total_amount': 3000,
            'amount_paid': 0,
            'change_amount': 0,
            'payment_method': 'credit',
            'items': [
                {
                    'product_id': product.pk,
                    'quantity': 1,
                    'unit_price': 3000,
                    'total_price': 3000,
                }
            ]
        }
        response = client.post(
            reverse('pos:create_sale'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 200
        assert response.json()['success'] is True

    def test_create_sale_get_not_allowed(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('pos:create_sale'))
        assert response.status_code == 405

    def test_admin_cannot_access_cashier_view(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('pos:cashier'))
        assert response.status_code == 302  # Redirected


@pytest.mark.django_db
class TestPOSCreateCustomerForm:
    """Tests for POS inline customer creation (AJAX)"""

    def test_create_customer_from_pos(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        data = {
            'name': 'Quick Customer',
            'phone': '+225 01 02 03 04',
        }
        response = client.post(
            reverse('pos:create_customer'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['customer_name'] == 'Quick Customer'
        assert Customer.objects.filter(name='Quick Customer').exists()

    def test_create_customer_missing_name(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        data = {'name': '', 'phone': '123'}
        response = client.post(
            reverse('pos:create_customer'),
            data=json.dumps(data),
            content_type='application/json',
        )
        assert response.status_code == 400


# ============================================================================
# 8. STOCK ENTRY FORM
# ============================================================================

@pytest.mark.django_db
class TestStockEntryForm:
    """Tests for stock entry form"""

    def test_stock_entry_page_loads(self, stock_manager_user_with_enterprise):
        client = login_client(stock_manager_user_with_enterprise)
        response = client.get(reverse('stock:entry'))
        assert response.status_code == 200

    def test_stock_entry_success(self, stock_manager_user_with_enterprise):
        enterprise = stock_manager_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Test Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(stock_manager_user_with_enterprise)
        response = client.post(reverse('stock:entry'), {
            'product': product.pk,
            'quantity': '50',
            'unit_cost': '500',
            'reason': 'purchase',
            'reference': 'INV-2025-001',
            'notes': 'Livraison fournisseur',
        })
        assert response.status_code == 302
        assert StockMovement.objects.filter(product=product).exists()
        movement = StockMovement.objects.get(product=product)
        assert movement.quantity == Decimal('50')
        assert movement.movement_type == 'entry'
        assert movement.reason == 'purchase'
        # Verify stock updated
        stock = Stock.objects.get(product=product)
        assert stock.quantity == Decimal('50')
        assert StockMovement.objects.filter(product=product).exists()
        movement = StockMovement.objects.get(product=product)
        assert movement.quantity == Decimal('50')
        assert movement.movement_type == 'entry'
        assert movement.reason == 'purchase'
        # Verify stock updated
        stock = Stock.objects.get(product=product)
        assert stock.quantity == Decimal('50')

    def test_stock_entry_with_location(self, stock_manager_user_with_enterprise, location_warehouse):
        enterprise = stock_manager_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Located Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(stock_manager_user_with_enterprise)
        response = client.post(reverse('stock:entry'), {
            'product': product.pk,
            'quantity': '25',
            'reason': 'purchase',
            'location': location_warehouse.pk,
        })
        assert response.status_code == 302
        movement = StockMovement.objects.get(product=product)
        assert movement.location == location_warehouse

    def test_stock_entry_invalid_product(self, stock_manager_user_with_enterprise):
        client = login_client(stock_manager_user_with_enterprise)
        response = client.post(reverse('stock:entry'), {
            'product': '99999',
            'quantity': '50',
            'reason': 'purchase',
        })
        assert response.status_code == 200  # Re-renders with error

    def test_cashier_cannot_access_stock_entry(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('stock:entry'))
        assert response.status_code == 302


# ============================================================================
# 9. EXPENSE CATEGORY FORMS
# ============================================================================

@pytest.mark.django_db
class TestExpenseCategoryForms:
    """Tests for expense category create/edit"""

    def test_create_expense_category_success(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_category_create'), {
            'name': 'Transport',
            'description': 'Frais de transport',
        })
        assert response.status_code == 302
        assert ExpenseCategory.objects.filter(name='Transport').exists()

    def test_create_expense_category_empty_name(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_category_create'), {
            'name': '',
        })
        assert response.status_code == 200
        assert ExpenseCategory.objects.count() == 0

    def test_create_expense_category_duplicate(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        ExpenseCategory.objects.create(name='Loyer', enterprise=enterprise)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_category_create'), {
            'name': 'Loyer',
        })
        assert response.status_code == 200
        assert ExpenseCategory.objects.filter(name='Loyer').count() == 1

    def test_edit_expense_category_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = ExpenseCategory.objects.create(
            name='Old Name', enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(
            reverse('accounting:expense_category_edit', args=[category.pk]), {
                'name': 'New Name',
                'description': 'Updated',
                'is_active': 'on',
            }
        )
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.name == 'New Name'


# ============================================================================
# 10. EXPENSE FORMS
# ============================================================================

@pytest.mark.django_db
class TestExpenseCreateForm:
    """Tests for expense creation"""

    def test_expense_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('accounting:expense_create'))
        assert response.status_code == 200

    def test_create_expense_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        exp_cat = ExpenseCategory.objects.create(
            name='Utilities', enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_create'), {
            'description': 'Facture électricité janvier',
            'amount': '75000',
            'expense_date': '2025-01-15',
            'category': exp_cat.pk,
            'payment_method': 'cash',
            'supplier': 'CIE',
            'reference': 'FACT-2025-001',
        })
        assert response.status_code == 302
        expense = Expense.objects.first()
        assert expense.amount == Decimal('75000')
        assert expense.description == 'Facture électricité janvier'

    def test_create_expense_missing_description(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_create'), {
            'description': '',
            'amount': '5000',
            'expense_date': '2025-01-15',
            'payment_method': 'cash',
        })
        assert response.status_code == 200
        assert Expense.objects.count() == 0

    def test_create_expense_zero_amount(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_create'), {
            'description': 'Zero expense',
            'amount': '0',
            'expense_date': '2025-01-15',
            'payment_method': 'cash',
        })
        assert response.status_code == 200
        assert Expense.objects.count() == 0

    def test_create_expense_missing_date(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_create'), {
            'description': 'No date expense',
            'amount': '5000',
            'expense_date': '',
            'payment_method': 'cash',
        })
        assert response.status_code == 200
        assert Expense.objects.count() == 0

    def test_create_expense_with_recurring(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_create'), {
            'description': 'Loyer mensuel',
            'amount': '150000',
            'expense_date': '2025-01-01',
            'payment_method': 'bank_transfer',
            'is_recurring': 'on',
        })
        assert response.status_code == 302
        expense = Expense.objects.first()
        assert expense.is_recurring is True


@pytest.mark.django_db
class TestExpenseEditForm:
    """Tests for expense editing"""

    def test_edit_expense_success(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        expense = Expense.objects.create(
            description='Original',
            amount=Decimal('5000'),
            expense_date='2025-01-15',
            payment_method='cash',
            user=admin_user_with_enterprise,
            enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_edit', args=[expense.pk]), {
            'description': 'Updated Description',
            'amount': '7500',
            'expense_date': '2025-01-20',
            'payment_method': 'mobile_money',
        })
        assert response.status_code == 302
        expense.refresh_from_db()
        assert expense.description == 'Updated Description'
        assert expense.amount == Decimal('7500')


# ============================================================================
# 11. CASH REGISTER SESSION FORMS
# ============================================================================

@pytest.mark.django_db
class TestCashSessionOpenForm:
    """Tests for opening cash register session"""

    def test_cash_session_open_page_loads(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounting:cash_session_open'))
        assert response.status_code == 200

    def test_open_session_success(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_open'), {
            'opening_balance': '25000',
            'notes': 'Ouverture matin',
        })
        assert response.status_code == 302
        session = CashRegisterSession.objects.first()
        assert session.opening_balance == Decimal('25000')
        assert session.status == 'open'
        assert session.user == cashier_user_with_enterprise

    def test_open_session_zero_balance(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_open'), {
            'opening_balance': '0',
        })
        assert response.status_code == 302
        assert CashRegisterSession.objects.count() == 1

    def test_open_session_negative_balance(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_open'), {
            'opening_balance': '-5000',
        })
        assert response.status_code == 200
        assert CashRegisterSession.objects.count() == 0

    def test_cannot_open_duplicate_session(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        CashRegisterSession.objects.create(
            user=cashier_user_with_enterprise,
            enterprise=enterprise,
            opening_balance=Decimal('10000'),
            opened_at=timezone.now(),
            status='open',
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounting:cash_session_open'))
        assert response.status_code == 302  # Redirected to existing session

    def test_open_session_with_location(self, cashier_user_with_enterprise, location_boutique):
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_open'), {
            'opening_balance': '30000',
            'location': location_boutique.pk,
        })
        assert response.status_code == 302
        session = CashRegisterSession.objects.first()
        assert session.location == location_boutique


@pytest.mark.django_db
class TestCashSessionCloseForm:
    """Tests for closing cash register session"""

    def test_close_session_success(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        session = CashRegisterSession.objects.create(
            user=cashier_user_with_enterprise,
            enterprise=enterprise,
            opening_balance=Decimal('25000'),
            opened_at=timezone.now(),
            status='open',
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_close', args=[session.pk]), {
            'closing_balance': '85000',
            'notes': 'Bonne journée',
        })
        assert response.status_code == 302
        session.refresh_from_db()
        assert session.status == 'closed'
        assert session.closing_balance == Decimal('85000')
        assert session.difference == Decimal('60000')  # 85000 - 25000

    def test_close_session_negative_balance(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        session = CashRegisterSession.objects.create(
            user=cashier_user_with_enterprise,
            enterprise=enterprise,
            opening_balance=Decimal('25000'),
            opened_at=timezone.now(),
            status='open',
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.post(reverse('accounting:cash_session_close', args=[session.pk]), {
            'closing_balance': '-1000',
        })
        assert response.status_code == 200
        session.refresh_from_db()
        assert session.status == 'open'  # Not closed

    def test_close_already_closed_session(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        session = CashRegisterSession.objects.create(
            user=cashier_user_with_enterprise,
            enterprise=enterprise,
            opening_balance=Decimal('25000'),
            closing_balance=Decimal('50000'),
            opened_at=timezone.now(),
            status='closed',
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounting:cash_session_close', args=[session.pk]))
        assert response.status_code == 302  # Redirected


# ============================================================================
# 12. TRANSFER FORMS
# ============================================================================

@pytest.mark.django_db
class TestTransferCreateForm:
    """Tests for transfer creation"""

    def test_transfer_create_page_loads(self, admin_user_with_enterprise):
        client = login_client(admin_user_with_enterprise)
        response = client.get(reverse('transfers:create'))
        assert response.status_code == 200

    def test_create_transfer_success(self, admin_user_with_enterprise, location_warehouse, location_boutique):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Transfer Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        LocationStock.objects.create(
            location=location_warehouse, product=product, quantity=100,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'notes': 'Réapprovisionnement boutique',
            'product_id': [product.pk],
            'quantity': ['20'],
        })
        assert response.status_code == 302
        assert Transfer.objects.count() == 1
        transfer = Transfer.objects.first()
        assert transfer.source_location == location_warehouse
        assert transfer.destination_location == location_boutique
        assert transfer.status == 'draft'
        assert TransferItem.objects.filter(transfer=transfer).count() == 1

    def test_create_transfer_quantity_exceeds_source_stock(self, admin_user_with_enterprise, location_warehouse, location_boutique):
        """A transfer requesting more than the source's available stock is rejected."""
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Scarce Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        LocationStock.objects.create(
            location=location_warehouse, product=product, quantity=5,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'notes': '',
            'product_id': [product.pk],
            'quantity': ['20'],
        }, follow=True)
        assert Transfer.objects.count() == 0
        messages = [str(m) for m in response.context['messages']]
        assert any('Stock insuffisant' in m for m in messages)

    def test_create_transfer_no_stock_at_source(self, admin_user_with_enterprise, location_warehouse, location_boutique):
        """A product with no stock row at the source cannot be transferred."""
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Absent Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'notes': '',
            'product_id': [product.pk],
            'quantity': ['20'],
        }, follow=True)
        assert Transfer.objects.count() == 0
        messages = [str(m) for m in response.context['messages']]
        assert any('Stock insuffisant' in m for m in messages)

    def test_create_transfer_same_location(self, admin_user_with_enterprise, location_warehouse):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_warehouse.pk,
            'product_id': [product.pk],
            'quantity': ['10'],
        })
        assert response.status_code == 302  # Redirected with error
        assert Transfer.objects.count() == 0

    def test_create_transfer_no_items(self, admin_user_with_enterprise, location_warehouse, location_boutique):
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'product_id': [],
            'quantity': [],
        })
        assert response.status_code == 302  # Redirected with error
        assert Transfer.objects.count() == 0

    def test_create_transfer_multiple_items(
        self, admin_user_with_enterprise, location_warehouse, location_boutique,
    ):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product1 = Product.objects.create(
            name='Product 1', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        product2 = Product.objects.create(
            name='Product 2', category=category,
            purchase_price=1000, sale_price=1500, enterprise=enterprise,
        )
        LocationStock.objects.create(location=location_warehouse, product=product1, quantity=50)
        LocationStock.objects.create(location=location_warehouse, product=product2, quantity=50)
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'product_id': [product1.pk, product2.pk],
            'quantity': ['10', '20'],
        })
        assert response.status_code == 302
        transfer = Transfer.objects.first()
        assert TransferItem.objects.filter(transfer=transfer).count() == 2


@pytest.mark.django_db
class TestTransferSendForm:
    """Tests for sending a transfer"""

    def test_send_transfer_success(self, admin_user_with_enterprise, location_warehouse, location_boutique):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        # Create stock at source location
        LocationStock.objects.create(
            location=location_warehouse, product=product, quantity=100,
        )
        transfer = Transfer.objects.create(
            enterprise=enterprise,
            source_location=location_warehouse,
            destination_location=location_boutique,
            created_by=admin_user_with_enterprise,
            status='draft',
        )
        TransferItem.objects.create(
            transfer=transfer, product=product, quantity=20,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:send', args=[transfer.pk]))
        assert response.status_code == 302
        transfer.refresh_from_db()
        assert transfer.status == 'in_transit'
        # Verify stock deducted from source
        loc_stock = LocationStock.objects.get(location=location_warehouse, product=product)
        assert loc_stock.quantity == Decimal('80')

    def test_send_transfer_insufficient_stock(
        self, admin_user_with_enterprise, location_warehouse, location_boutique,
    ):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        LocationStock.objects.create(
            location=location_warehouse, product=product, quantity=5,
        )
        transfer = Transfer.objects.create(
            enterprise=enterprise,
            source_location=location_warehouse,
            destination_location=location_boutique,
            created_by=admin_user_with_enterprise,
            status='draft',
        )
        TransferItem.objects.create(
            transfer=transfer, product=product, quantity=50,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:send', args=[transfer.pk]))
        assert response.status_code == 302
        transfer.refresh_from_db()
        assert transfer.status == 'draft'  # Not sent


@pytest.mark.django_db
class TestTransferReceiveForm:
    """Tests for receiving a transfer"""

    def test_receive_transfer_success(
        self, admin_user_with_enterprise, location_warehouse, location_boutique,
    ):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        transfer = Transfer.objects.create(
            enterprise=enterprise,
            source_location=location_warehouse,
            destination_location=location_boutique,
            created_by=admin_user_with_enterprise,
            status='in_transit',
        )
        TransferItem.objects.create(
            transfer=transfer, product=product, quantity=20,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:receive', args=[transfer.pk]))
        assert response.status_code == 302
        transfer.refresh_from_db()
        assert transfer.status == 'received'
        # Verify stock added to destination
        loc_stock = LocationStock.objects.get(
            location=location_boutique, product=product,
        )
        assert loc_stock.quantity == Decimal('20')

    def test_receive_transfer_with_adjusted_quantities(
        self, admin_user_with_enterprise, location_warehouse, location_boutique,
    ):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        transfer = Transfer.objects.create(
            enterprise=enterprise,
            source_location=location_warehouse,
            destination_location=location_boutique,
            created_by=admin_user_with_enterprise,
            status='in_transit',
        )
        item = TransferItem.objects.create(
            transfer=transfer, product=product, quantity=20,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:receive', args=[transfer.pk]), {
            f'received_qty_{item.pk}': '18',  # Received less
        })
        assert response.status_code == 302
        transfer.refresh_from_db()
        assert transfer.status == 'received'
        loc_stock = LocationStock.objects.get(
            location=location_boutique, product=product,
        )
        assert loc_stock.quantity == Decimal('18')


@pytest.mark.django_db
class TestTransferCancelForm:
    """Tests for cancelling a transfer"""

    def test_cancel_draft_transfer(
        self, admin_user_with_enterprise, location_warehouse, location_boutique,
    ):
        enterprise = admin_user_with_enterprise.enterprise
        transfer = Transfer.objects.create(
            enterprise=enterprise,
            source_location=location_warehouse,
            destination_location=location_boutique,
            created_by=admin_user_with_enterprise,
            status='draft',
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('transfers:cancel', args=[transfer.pk]), {
            'reason': 'Erreur de saisie',
        })
        assert response.status_code == 302
        transfer.refresh_from_db()
        assert transfer.status == 'cancelled'
        assert transfer.cancellation_reason == 'Erreur de saisie'


# ============================================================================
# 13. PRODUCT SEARCH FORM (POS)
# ============================================================================

@pytest.mark.django_db
class TestProductSearchForm:
    """Tests for POS product search"""

    def test_search_products(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        category = Category.objects.create(name='Drinks', enterprise=enterprise)
        Product.objects.create(
            name='Coca Cola', category=category,
            purchase_price=300, sale_price=500, enterprise=enterprise,
        )
        Product.objects.create(
            name='Fanta Orange', category=category,
            purchase_price=300, sale_price=500, enterprise=enterprise,
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('pos:search_products'), {'q': 'coca'})
        assert response.status_code == 200

    def test_search_products_by_category(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        cat1 = Category.objects.create(name='Drinks', enterprise=enterprise)
        cat2 = Category.objects.create(name='Food', enterprise=enterprise)
        Product.objects.create(
            name='Water', category=cat1,
            purchase_price=100, sale_price=200, enterprise=enterprise,
        )
        Product.objects.create(
            name='Bread', category=cat2,
            purchase_price=200, sale_price=350, enterprise=enterprise,
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.get(
            reverse('pos:search_products'),
            {'category': cat1.pk},
        )
        assert response.status_code == 200

    def test_search_by_barcode(self, cashier_user_with_enterprise):
        enterprise = cashier_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        Product.objects.create(
            name='Barcode Product', category=category,
            barcode='1234567890', purchase_price=300,
            sale_price=500, enterprise=enterprise,
        )
        client = login_client(cashier_user_with_enterprise)
        response = client.get(
            reverse('pos:search_products'),
            {'q': '1234567890'},
        )
        assert response.status_code == 200


# ============================================================================
# 14. DELETE / TOGGLE FORMS (POST-only actions)
# ============================================================================

@pytest.mark.django_db
class TestDeleteAndToggleForms:
    """Tests for deletion and toggle forms"""

    def test_toggle_product_active(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Toggle Product', category=category,
            purchase_price=500, sale_price=750,
            is_active=True, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_toggle', args=[product.pk]))
        assert response.status_code == 302
        product.refresh_from_db()
        assert product.is_active is False

    def test_toggle_category_active(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(
            name='Toggle Cat', enterprise=enterprise, is_active=True,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_toggle', args=[category.pk]))
        assert response.status_code == 302
        category.refresh_from_db()
        assert category.is_active is False

    def test_toggle_customer_active(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        customer = Customer.objects.create(
            name='Toggle Customer', enterprise=enterprise, is_active=True,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('customers:customer_toggle', args=[customer.pk]))
        assert response.status_code == 302
        customer.refresh_from_db()
        assert customer.is_active is False

    def test_delete_product_no_history(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Cat', enterprise=enterprise)
        product = Product.objects.create(
            name='Delete Me', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:product_delete', args=[product.pk]))
        assert response.status_code == 302
        assert not Product.objects.filter(pk=product.pk).exists()

    def test_delete_category_with_products_blocked(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        category = Category.objects.create(name='Has Products', enterprise=enterprise)
        Product.objects.create(
            name='Child Product', category=category,
            purchase_price=500, sale_price=750, enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('products:category_delete', args=[category.pk]))
        assert response.status_code == 302
        assert Category.objects.filter(pk=category.pk).exists()  # Not deleted

    def test_delete_expense(self, admin_user_with_enterprise):
        enterprise = admin_user_with_enterprise.enterprise
        expense = Expense.objects.create(
            description='Delete Me',
            amount=Decimal('5000'),
            expense_date='2025-01-15',
            payment_method='cash',
            user=admin_user_with_enterprise,
            enterprise=enterprise,
        )
        client = login_client(admin_user_with_enterprise)
        response = client.post(reverse('accounting:expense_delete', args=[expense.pk]))
        assert response.status_code == 302
        assert not Expense.objects.filter(pk=expense.pk).exists()


# ============================================================================
# 15. PERMISSION / ACCESS CONTROL TESTS
# ============================================================================

@pytest.mark.django_db
class TestFormAccessControl:
    """Tests that forms enforce role-based access"""

    def test_unauthenticated_redirects_to_login(self):
        client = Client()
        protected_urls = [
            reverse('products:product_create'),
            reverse('customers:customer_create'),
            reverse('accounting:expense_create'),
            reverse('accounts:user_create'),
        ]
        for url in protected_urls:
            response = client.get(url)
            assert response.status_code == 302, f"URL {url} not protected"

    def test_accountant_cannot_create_products(self, accountant_user_with_enterprise):
        client = login_client(accountant_user_with_enterprise)
        response = client.get(reverse('products:product_create'))
        assert response.status_code == 302  # Redirected

    def test_cashier_cannot_create_users(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounts:user_create'))
        assert response.status_code == 302

    def test_cashier_cannot_create_expenses(self, cashier_user_with_enterprise):
        client = login_client(cashier_user_with_enterprise)
        response = client.get(reverse('accounting:expense_create'))
        assert response.status_code == 302

    def test_stock_manager_cannot_access_pos(self, stock_manager_user_with_enterprise):
        client = login_client(stock_manager_user_with_enterprise)
        response = client.get(reverse('pos:cashier'))
        assert response.status_code == 302
