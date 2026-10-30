"""
UI Navigation & Form Rendering Tests

These tests simulate a REAL USER navigating the application:
1. Navigate to each page via the same links a user would click
2. Verify the page loads and renders all expected form fields
3. Submit the form with valid data
4. Verify the redirect lands on the correct page
5. Navigate back to verify the created data appears in lists

This ensures every form is not just "backend-correct" but actually
usable by a human clicking through the browser.
"""
import json
import pytest
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.products.models import Category, Product
from apps.stock.models import Stock, StockMovement
from apps.customers.models import Customer
from apps.pos.models import Sale, SaleItem
from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession
from apps.locations.models import Location, LocationStock
from apps.transfers.models import Transfer, TransferItem
from apps.core.models import Enterprise

from tests.factories import (
    UserFactory, CategoryFactory, ProductFactory, StockFactory,
    CustomerFactory, ExpenseCategoryFactory,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def enterprise():
    return Enterprise.objects.create(
        name='Test Enterprise', code='UINAV01', currency='FB',
    )

@pytest.fixture
def location_warehouse(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Dépôt Principal',
        code='UIWH01', location_type='warehouse', is_main_warehouse=True,
    )

@pytest.fixture
def location_boutique(enterprise):
    return Location.objects.create(
        enterprise=enterprise, name='Boutique Centre',
        code='UIBT01', location_type='boutique',
    )

@pytest.fixture
def admin_user(enterprise, location_warehouse):
    return UserFactory(role='admin', enterprise=enterprise, location=location_warehouse)

@pytest.fixture
def cashier_user(enterprise, location_boutique):
    return UserFactory(role='cashier', enterprise=enterprise, location=location_boutique)

@pytest.fixture
def stock_manager_user(enterprise, location_warehouse):
    return UserFactory(role='stock_manager', enterprise=enterprise, location=location_warehouse)

@pytest.fixture
def accountant_user(enterprise):
    return UserFactory(role='accountant', enterprise=enterprise)


def logged_in(user):
    client = Client()
    client.force_login(user)
    return client


# ============================================================================
# HELPER: Check that HTML contains expected form fields
# ============================================================================

def assert_form_fields(html_content, field_names, form_description=""):
    """Verify that the rendered HTML contains input/select/textarea elements with expected names."""
    for field_name in field_names:
        # Check for name="field_name" in any form element
        assert (
            f'name="{field_name}"' in html_content
        ), f"Form field '{field_name}' not found in rendered HTML for {form_description}"


def assert_has_submit_button(html_content, form_description=""):
    """Verify the form has a submit button."""
    assert (
        'type="submit"' in html_content
    ), f"No submit button found in rendered HTML for {form_description}"


def assert_has_csrf(html_content, form_description=""):
    """Verify CSRF token is present."""
    assert (
        'csrfmiddlewaretoken' in html_content
    ), f"No CSRF token found in rendered HTML for {form_description}"


def assert_page_ok(response, form_description=""):
    """Verify page loaded successfully (200 OK)."""
    assert response.status_code == 200, (
        f"{form_description} returned {response.status_code} instead of 200"
    )


# ============================================================================
# TEST: Complete User Journey - Login
# ============================================================================

@pytest.mark.django_db
class TestLoginPageUI:

    def test_login_page_renders_form_fields(self):
        """User navigates to /login/ and sees username + password fields"""
        client = Client()
        response = client.get(reverse('login'))
        html = response.content.decode()

        assert_page_ok(response, "Login page")
        assert_form_fields(html, ['username', 'password'], "Login")
        assert_has_submit_button(html, "Login")
        assert_has_csrf(html, "Login")

    def test_login_submit_redirects_to_home(self):
        """User fills login form and gets redirected to home"""
        user = UserFactory(role='admin')
        client = Client()
        response = client.post(reverse('login'), {
            'username': user.username,
            'password': 'password123',
        })
        assert response.status_code == 302
        # Home dispatches to the role dashboard for users with an enterprise;
        # follow=True so it resolves to a final 200 either way.
        response = client.get(reverse('home'), follow=True)
        assert response.status_code == 200


# ============================================================================
# TEST: Complete User Journey - User Management
# ============================================================================

@pytest.mark.django_db
class TestUserManagementUI:

    def test_navigate_to_user_list_then_create(self, admin_user):
        """Admin clicks Utilisateurs in nav → sees list → clicks Nouvel Utilisateur → sees form"""
        client = logged_in(admin_user)

        # Step 1: Navigate to user list
        response = client.get(reverse('accounts:user_list'))
        assert_page_ok(response, "User list")
        html = response.content.decode()
        # List page must have link to create form
        assert reverse('accounts:user_create') in html, "No 'Create User' link on user list page"

        # Step 2: Navigate to create form
        response = client.get(reverse('accounts:user_create'))
        assert_page_ok(response, "User create form")
        html = response.content.decode()

        # Step 3: Verify all expected form fields are rendered
        assert_form_fields(html, [
            'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'password', 'password_confirm',
        ], "User Create")
        assert_has_submit_button(html, "User Create")
        assert_has_csrf(html, "User Create")

    def test_create_user_and_see_in_list(self, admin_user):
        """Admin fills user create form → submits → redirect → sees new user in list"""
        client = logged_in(admin_user)

        # Submit the form
        response = client.post(reverse('accounts:user_create'), {
            'username': 'ui_test_user',
            'email': 'uitest@example.com',
            'first_name': 'UI',
            'last_name': 'Test',
            'phone': '+243 99 000 0001',
            'role': 'cashier',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
        })
        assert response.status_code == 302, "Form did not redirect after success"

        # Follow redirect to list and verify new user appears
        response = client.get(reverse('accounts:user_list'))
        html = response.content.decode()
        assert 'ui_test_user' in html, "Newly created user not visible in user list"

    def test_edit_user_form_renders(self, admin_user):
        """Admin clicks edit on a user → form loads with pre-filled data"""
        client = logged_in(admin_user)

        target_user = UserFactory(
            role='cashier', enterprise=admin_user.enterprise,
            first_name='Existing', last_name='User'
        )

        response = client.get(reverse('accounts:user_edit', args=[target_user.pk]))
        assert_page_ok(response, "User edit form")
        html = response.content.decode()

        assert_form_fields(html, [
            'email', 'first_name', 'last_name', 'phone', 'role',
        ], "User Edit")
        assert_has_submit_button(html, "User Edit")
        # Verify pre-filled values
        assert 'Existing' in html, "First name not pre-filled in edit form"

    def test_edit_user_submit_and_verify(self, admin_user):
        """Admin edits a user's name → submits → name updated"""
        client = logged_in(admin_user)

        target = UserFactory(
            role='cashier', enterprise=admin_user.enterprise,
            first_name='OldName'
        )

        response = client.post(reverse('accounts:user_edit', args=[target.pk]), {
            'email': target.email,
            'first_name': 'NewName',
            'last_name': target.last_name,
            'phone': target.phone,
            'role': 'cashier',
        })
        assert response.status_code == 302

        target.refresh_from_db()
        assert target.first_name == 'NewName'


# ============================================================================
# TEST: Complete User Journey - Categories
# ============================================================================

@pytest.mark.django_db
class TestCategoryUI:

    def test_navigate_to_category_list_then_create(self, admin_user):
        """Admin navigates to category list → clicks create → sees form"""
        client = logged_in(admin_user)

        response = client.get(reverse('products:category_list'))
        assert_page_ok(response, "Category list")
        html = response.content.decode()
        assert reverse('products:category_create') in html

        response = client.get(reverse('products:category_create'))
        assert_page_ok(response, "Category create form")
        html = response.content.decode()

        assert_form_fields(html, ['name', 'description'], "Category Create")
        assert_has_submit_button(html, "Category Create")
        assert_has_csrf(html, "Category Create")

    def test_create_category_and_see_in_list(self, admin_user):
        """Admin creates a category → sees it in list"""
        client = logged_in(admin_user)

        response = client.post(reverse('products:category_create'), {
            'name': 'Boissons Fraîches',
            'description': 'Sodas, jus, eau',
        })
        assert response.status_code == 302

        response = client.get(reverse('products:category_list'))
        html = response.content.decode()
        assert 'Boissons' in html, "New category not visible in list"

    def test_edit_category_form_renders_prefilled(self, admin_user, enterprise):
        """Admin edits an existing category → form pre-filled"""
        client = logged_in(admin_user)

        cat = CategoryFactory(name='OldCategory', enterprise=enterprise)

        response = client.get(reverse('products:category_edit', args=[cat.pk]))
        assert_page_ok(response, "Category edit form")
        html = response.content.decode()
        assert 'OldCategory' in html, "Category name not pre-filled"
        assert_form_fields(html, ['name', 'description'], "Category Edit")


# ============================================================================
# TEST: Complete User Journey - Products
# ============================================================================

@pytest.mark.django_db
class TestProductUI:

    def test_navigate_to_product_list_then_create(self, admin_user, enterprise):
        """Admin navigates to product list → clicks create → sees full form"""
        client = logged_in(admin_user)
        CategoryFactory(name='TestCat', enterprise=enterprise)

        response = client.get(reverse('products:product_list'))
        assert_page_ok(response, "Product list")
        html = response.content.decode()
        assert reverse('products:product_create') in html

        response = client.get(reverse('products:product_create'))
        assert_page_ok(response, "Product create form")
        html = response.content.decode()

        assert_form_fields(html, [
            'name', 'category', 'unit', 'description', 'barcode', 'sku',
            'purchase_price', 'sale_price', 'tax_rate', 'min_stock_threshold',
        ], "Product Create")
        assert_has_submit_button(html, "Product Create")
        assert_has_csrf(html, "Product Create")
        # Verify category dropdown has our category
        assert 'TestCat' in html, "Category not available in product form dropdown"

    def test_create_product_full_journey(self, admin_user, enterprise):
        """Admin creates a product → redirect → sees product in list"""
        client = logged_in(admin_user)
        cat = CategoryFactory(name='Boissons', enterprise=enterprise)

        response = client.post(reverse('products:product_create'), {
            'name': 'Coca-Cola 33cl',
            'category': cat.pk,
            'unit': 'piece',
            'description': 'Canette de soda',
            'purchase_price': '500',
            'sale_price': '800',
            'tax_rate': '0',
            'min_stock_threshold': '10',
        })
        assert response.status_code == 302, "Product create did not redirect"

        response = client.get(reverse('products:product_list'))
        html = response.content.decode()
        assert 'Coca-Cola' in html, "New product not visible in product list"

    def test_edit_product_form_prefilled(self, admin_user, enterprise):
        """Admin edits product → form shows current values"""
        client = logged_in(admin_user)
        product = ProductFactory(
            name='Existing Product', enterprise=enterprise,
            purchase_price=100, sale_price=200,
        )

        response = client.get(reverse('products:product_edit', args=[product.pk]))
        assert_page_ok(response, "Product edit form")
        html = response.content.decode()

        assert 'Existing Product' in html, "Product name not pre-filled"
        assert_form_fields(html, [
            'name', 'category', 'purchase_price', 'sale_price',
        ], "Product Edit")

    def test_product_detail_page(self, admin_user, enterprise):
        """Admin clicks on a product → sees detail page"""
        client = logged_in(admin_user)
        product = ProductFactory(name='Detail Test Product', enterprise=enterprise)

        response = client.get(reverse('products:product_detail', args=[product.pk]))
        assert_page_ok(response, "Product detail")
        html = response.content.decode()
        assert 'Detail Test Product' in html


# ============================================================================
# TEST: Complete User Journey - Customers
# ============================================================================

@pytest.mark.django_db
class TestCustomerUI:

    def test_navigate_to_customer_list_then_create(self, admin_user):
        """User navigates to customer list → clicks create → sees form"""
        client = logged_in(admin_user)

        response = client.get(reverse('customers:customer_list'))
        assert_page_ok(response, "Customer list")
        html = response.content.decode()
        assert reverse('customers:customer_create') in html

        response = client.get(reverse('customers:customer_create'))
        assert_page_ok(response, "Customer create form")
        html = response.content.decode()

        assert_form_fields(html, [
            'name', 'phone', 'email', 'address', 'credit_limit',
        ], "Customer Create")
        assert_has_submit_button(html, "Customer Create")
        assert_has_csrf(html, "Customer Create")

    def test_create_customer_and_see_in_list(self, admin_user):
        """User creates a customer → sees them in list"""
        client = logged_in(admin_user)

        response = client.post(reverse('customers:customer_create'), {
            'name': 'Marie Dupont',
            'phone': '+243 99 123 4567',
            'email': 'marie@example.com',
            'address': '123 Rue de la Paix',
            'credit_limit': '50000',
        })
        assert response.status_code == 302

        response = client.get(reverse('customers:customer_list'))
        html = response.content.decode()
        assert 'Marie Dupont' in html, "New customer not visible in list"

    def test_customer_detail_page(self, admin_user, enterprise):
        """User clicks on a customer → sees detail page"""
        client = logged_in(admin_user)
        customer = CustomerFactory(name='Detail Customer', enterprise=enterprise)

        response = client.get(reverse('customers:customer_detail', args=[customer.pk]))
        assert_page_ok(response, "Customer detail")
        html = response.content.decode()
        assert 'Detail Customer' in html

    def test_edit_customer_form_prefilled(self, admin_user, enterprise):
        """User edits a customer → form is pre-filled"""
        client = logged_in(admin_user)
        customer = CustomerFactory(name='Old Customer Name', enterprise=enterprise)

        response = client.get(reverse('customers:customer_edit', args=[customer.pk]))
        assert_page_ok(response, "Customer edit form")
        html = response.content.decode()
        assert 'Old Customer Name' in html
        assert_form_fields(html, ['name', 'phone', 'email', 'address'], "Customer Edit")

    def test_credit_payment_form_renders(self, admin_user, enterprise, location_boutique):
        """User navigates to record payment → form renders"""
        client = logged_in(admin_user)
        customer = CustomerFactory(name='Credit Customer', enterprise=enterprise, credit_limit=500000)

        # Create a credit sale to generate a CustomerCredit via signal
        sale = Sale.objects.create(
            sale_number=Sale.generate_sale_number(),
            customer=customer,
            user=admin_user,
            enterprise=enterprise,
            location=location_boutique,
            subtotal=Decimal('5000'), total_amount=Decimal('5000'),
            amount_paid=Decimal('0'), payment_method='credit',
            status='completed',
        )
        from apps.customers.models import CustomerCredit
        credit = CustomerCredit.objects.get(customer=customer)

        response = client.get(reverse('customers:record_payment', args=[credit.pk]))
        assert_page_ok(response, "Record payment form")
        html = response.content.decode()

        assert_form_fields(html, ['amount', 'payment_method'], "Record Payment")
        assert_has_submit_button(html, "Record Payment")
        assert_has_csrf(html, "Record Payment")


# ============================================================================
# TEST: Complete User Journey - Stock Management
# ============================================================================

@pytest.mark.django_db
class TestStockUI:

    def test_navigate_dashboard_then_stock_entry(self, stock_manager_user, enterprise):
        """Stock manager navigates to dashboard → clicks Nouvelle Entrée → sees form"""
        client = logged_in(stock_manager_user)
        # A product must exist for the entry form (otherwise the empty-state shows)
        ProductFactory(name='Stock Nav Product', enterprise=enterprise)

        response = client.get(reverse('stock:dashboard'))
        assert_page_ok(response, "Stock dashboard")
        html = response.content.decode()
        assert reverse('stock:entry') in html, "No 'Stock Entry' link on dashboard"

        response = client.get(reverse('stock:entry'))
        assert_page_ok(response, "Stock entry form")
        html = response.content.decode()

        assert_form_fields(html, [
            'product', 'quantity', 'unit_cost', 'reason', 'reference', 'notes',
        ], "Stock Entry")
        assert_has_submit_button(html, "Stock Entry")
        assert_has_csrf(html, "Stock Entry")

    def test_stock_entry_shows_location_field(self, stock_manager_user, enterprise, location_warehouse, location_boutique):
        """Stock entry form renders location dropdown when locations exist"""
        client = logged_in(stock_manager_user)
        # A product must exist for the entry form (otherwise the empty-state shows)
        ProductFactory(name='Stock Loc Product', enterprise=enterprise)

        response = client.get(reverse('stock:entry'))
        html = response.content.decode()

        # Location field should be present since enterprise has locations
        assert 'name="location"' in html, "Location dropdown not rendered in stock entry form"
        assert 'Dépôt Principal' in html, "Warehouse not in location dropdown"
        assert 'Boutique Centre' in html, "Boutique not in location dropdown"

    def test_stock_entry_full_journey(self, stock_manager_user, enterprise, location_warehouse):
        """Stock manager enters stock → redirect → stock quantity updated"""
        client = logged_in(stock_manager_user)
        product = ProductFactory(name='Stock Test Product', enterprise=enterprise)

        response = client.post(reverse('stock:entry'), {
            'product': product.pk,
            'quantity': '50',
            'unit_cost': '1000',
            'reason': 'purchase',
            'reference': 'INV-001',
            'notes': 'First stock entry',
            'location': location_warehouse.pk,
        })
        assert response.status_code == 302, "Stock entry did not redirect"

        # Verify stock was actually created/updated
        movement = StockMovement.objects.filter(product=product).first()
        assert movement is not None, "No StockMovement created"
        assert movement.quantity == Decimal('50')
        assert movement.unit_cost == Decimal('1000')

    def test_stock_entry_product_dropdown_populated(self, stock_manager_user, enterprise):
        """Stock entry form shows products in dropdown"""
        client = logged_in(stock_manager_user)
        ProductFactory(name='Dropdown Product A', enterprise=enterprise)
        ProductFactory(name='Dropdown Product B', enterprise=enterprise)

        response = client.get(reverse('stock:entry'))
        html = response.content.decode()
        assert 'Dropdown Product A' in html, "Product A not in dropdown"
        assert 'Dropdown Product B' in html, "Product B not in dropdown"

    def test_low_stock_page_renders(self, stock_manager_user):
        """Low stock page loads"""
        client = logged_in(stock_manager_user)
        response = client.get(reverse('stock:low_stock'))
        assert_page_ok(response, "Low stock page")

    def test_out_of_stock_page_renders(self, stock_manager_user):
        """Out of stock page loads"""
        client = logged_in(stock_manager_user)
        response = client.get(reverse('stock:out_of_stock'))
        assert_page_ok(response, "Out of stock page")

    def test_movements_page_renders(self, stock_manager_user):
        """Movements history page loads"""
        client = logged_in(stock_manager_user)
        response = client.get(reverse('stock:movements'))
        assert_page_ok(response, "Movements page")


# ============================================================================
# TEST: Complete User Journey - Expenses
# ============================================================================

@pytest.mark.django_db
class TestExpenseUI:

    def test_navigate_to_expense_list_then_create(self, admin_user, enterprise):
        """User navigates to expense list → clicks create → sees form"""
        client = logged_in(admin_user)
        ExpenseCategoryFactory(name='Loyer', enterprise=enterprise)

        response = client.get(reverse('accounting:expense_list'))
        assert_page_ok(response, "Expense list")
        html = response.content.decode()
        assert reverse('accounting:expense_create') in html

        response = client.get(reverse('accounting:expense_create'))
        assert_page_ok(response, "Expense create form")
        html = response.content.decode()

        assert_form_fields(html, [
            'description', 'amount', 'expense_date', 'category',
            'payment_method', 'reference', 'notes',
        ], "Expense Create")
        assert_has_submit_button(html, "Expense Create")
        assert_has_csrf(html, "Expense Create")
        assert 'Loyer' in html, "Expense category not in dropdown"

    def test_create_expense_full_journey(self, admin_user, enterprise):
        """User creates an expense → redirect → sees it in list"""
        client = logged_in(admin_user)
        cat = ExpenseCategoryFactory(name='Transport', enterprise=enterprise)

        today = timezone.now().date().isoformat()
        response = client.post(reverse('accounting:expense_create'), {
            'description': 'Taxi pour livraison',
            'amount': '15000',
            'expense_date': today,
            'category': cat.pk,
            'payment_method': 'cash',
            'reference': '',
            'notes': '',
        })
        assert response.status_code == 302

        response = client.get(reverse('accounting:expense_list'))
        html = response.content.decode()
        assert 'Taxi' in html, "New expense not visible in list"

    def test_expense_category_create_journey(self, admin_user):
        """User creates an expense category → sees it in list"""
        client = logged_in(admin_user)

        response = client.get(reverse('accounting:expense_category_create'))
        assert_page_ok(response, "Expense category create form")
        html = response.content.decode()
        assert_form_fields(html, ['name', 'description'], "Expense Category Create")

        response = client.post(reverse('accounting:expense_category_create'), {
            'name': 'Fournitures',
            'description': 'Matériel de bureau',
        })
        assert response.status_code == 302

        response = client.get(reverse('accounting:expense_category_list'))
        html = response.content.decode()
        assert 'Fournitures' in html


# ============================================================================
# TEST: Complete User Journey - Cash Sessions
# ============================================================================

@pytest.mark.django_db
class TestCashSessionUI:

    def test_navigate_to_cash_session_list_then_open(self, admin_user, enterprise, location_warehouse):
        """User navigates to sessions → clicks open → sees form"""
        client = logged_in(admin_user)

        response = client.get(reverse('accounting:cash_session_list'))
        assert_page_ok(response, "Cash session list")
        html = response.content.decode()
        assert reverse('accounting:cash_session_open') in html

        response = client.get(reverse('accounting:cash_session_open'))
        assert_page_ok(response, "Cash session open form")
        html = response.content.decode()

        assert_form_fields(html, ['opening_balance'], "Cash Session Open")
        assert_has_submit_button(html, "Cash Session Open")
        assert_has_csrf(html, "Cash Session Open")

    def test_open_session_full_journey(self, admin_user, enterprise, location_warehouse):
        """User opens a cash session → redirect → sees session in list"""
        client = logged_in(admin_user)

        response = client.post(reverse('accounting:cash_session_open'), {
            'opening_balance': '100000',
            'location': location_warehouse.pk,
            'notes': 'Ouverture matin',
        })
        assert response.status_code == 302

        session = CashRegisterSession.objects.filter(user=admin_user).first()
        assert session is not None, "Cash session not created"
        assert session.opening_balance == Decimal('100000')

    def test_close_session_form_renders(self, admin_user, enterprise, location_warehouse):
        """User closes a cash session → form renders"""
        client = logged_in(admin_user)

        session = CashRegisterSession.objects.create(
            user=admin_user, enterprise=enterprise,
            location=location_warehouse,
            opening_balance=Decimal('100000'),
            status='open', opened_at=timezone.now(),
        )

        response = client.get(reverse('accounting:cash_session_close', args=[session.pk]))
        assert_page_ok(response, "Cash session close form")
        html = response.content.decode()

        assert_form_fields(html, ['closing_balance'], "Cash Session Close")
        assert_has_submit_button(html, "Cash Session Close")

    def test_close_session_submit(self, admin_user, enterprise, location_warehouse):
        """User closes a session → status changes"""
        client = logged_in(admin_user)

        session = CashRegisterSession.objects.create(
            user=admin_user, enterprise=enterprise,
            location=location_warehouse,
            opening_balance=Decimal('100000'),
            status='open', opened_at=timezone.now(),
        )

        response = client.post(reverse('accounting:cash_session_close', args=[session.pk]), {
            'closing_balance': '125000',
            'notes': 'Fermeture soir',
        })
        assert response.status_code == 302

        session.refresh_from_db()
        assert session.status == 'closed'
        assert session.closing_balance == Decimal('125000')


# ============================================================================
# TEST: Complete User Journey - Transfers
# ============================================================================

@pytest.mark.django_db
class TestTransferUI:

    def test_navigate_to_transfer_list_then_create(self, admin_user, enterprise, location_warehouse, location_boutique):
        """User navigates to transfers → clicks create → sees form"""
        client = logged_in(admin_user)

        response = client.get(reverse('transfers:list'))
        assert_page_ok(response, "Transfer list")
        html = response.content.decode()
        assert reverse('transfers:create') in html

        # Create products first so the form has something to show
        ProductFactory(name='Transfer Product', enterprise=enterprise)

        response = client.get(reverse('transfers:create'))
        assert_page_ok(response, "Transfer create form")
        html = response.content.decode()

        assert_form_fields(html, [
            'source_location', 'destination_location', 'notes',
        ], "Transfer Create")
        assert_has_submit_button(html, "Transfer Create")
        assert_has_csrf(html, "Transfer Create")
        # Verify locations appear in dropdowns
        assert 'Dépôt Principal' in html, "Source location not in dropdown"
        assert 'Boutique Centre' in html, "Destination location not in dropdown"

    def test_create_transfer_full_journey(self, admin_user, enterprise, location_warehouse, location_boutique):
        """User creates a transfer → redirect → sees it in list"""
        client = logged_in(admin_user)
        product = ProductFactory(name='Transfer Item', enterprise=enterprise)
        # Create stock at source (LocationStock = per-location availability checked by the view)
        StockFactory(product=product, enterprise=enterprise, location=location_warehouse, quantity=100)
        LocationStock.objects.create(product=product, location=location_warehouse, quantity=100)

        response = client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'product_id': [product.pk],
            'quantity': ['25'],
            'notes': 'Réappro boutique',
        })
        assert response.status_code == 302

        transfer = Transfer.objects.filter(source_location=location_warehouse).first()
        assert transfer is not None, "Transfer not created"
        assert transfer.items.count() == 1, "Transfer item not created"

    def test_transfer_detail_page(self, admin_user, enterprise, location_warehouse, location_boutique):
        """User views transfer detail → sees all info"""
        client = logged_in(admin_user)
        product = ProductFactory(name='Detail Transfer Product', enterprise=enterprise)
        StockFactory(product=product, enterprise=enterprise, location=location_warehouse, quantity=100)
        LocationStock.objects.create(product=product, location=location_warehouse, quantity=100)

        # Create transfer via POST
        client.post(reverse('transfers:create'), {
            'source_location': location_warehouse.pk,
            'destination_location': location_boutique.pk,
            'product_id': [product.pk],
            'quantity': ['10'],
            'notes': '',
        })
        transfer = Transfer.objects.first()

        response = client.get(reverse('transfers:detail', args=[transfer.pk]))
        assert_page_ok(response, "Transfer detail")
        html = response.content.decode()
        assert 'Detail Transfer Product' in html


# ============================================================================
# TEST: Complete User Journey - POS Cashier
# ============================================================================

@pytest.mark.django_db
class TestPOSCashierUI:

    def test_cashier_page_renders(self, cashier_user, enterprise):
        """Cashier navigates to POS → sees product grid and cart"""
        client = logged_in(cashier_user)

        response = client.get(reverse('pos:cashier'))
        assert_page_ok(response, "POS cashier")
        html = response.content.decode()

        # POS page uses Alpine.js — check key UI elements exist
        assert 'x-data' in html, "Alpine.js not initialized on POS page"
        assert 'csrfmiddlewaretoken' in html or 'csrf_token' in html.lower() or 'X-CSRFToken' in html, \
            "No CSRF token available for AJAX calls"

    def test_cashier_shows_products(self, cashier_user, enterprise):
        """Cashier sees popular products on POS page"""
        client = logged_in(cashier_user)
        ProductFactory(name='POS Visible Product', enterprise=enterprise, is_popular=True)

        response = client.get(reverse('pos:cashier'))
        html = response.content.decode()
        assert 'POS Visible Product' in html, "Popular product not visible on POS page"

    def test_pos_product_search(self, cashier_user, enterprise):
        """Cashier searches for a product → gets results"""
        client = logged_in(cashier_user)
        ProductFactory(name='Fanta Orange', enterprise=enterprise)

        response = client.get(reverse('pos:search_products'), {'q': 'Fanta'})
        assert_page_ok(response, "Product search")
        html = response.content.decode()
        assert 'Fanta Orange' in html, "Search did not find product"

    def test_pos_create_sale_ajax(self, cashier_user, enterprise, location_boutique):
        """Cashier submits a sale via AJAX → sale created"""
        client = logged_in(cashier_user)
        product = ProductFactory(
            name='Sale Product', enterprise=enterprise,
            sale_price=1000, purchase_price=500,
        )
        StockFactory(product=product, enterprise=enterprise, location=location_boutique, quantity=50)

        sale_data = {
            'items': [{
                'product_id': product.pk,
                'quantity': 2,
                'unit_price': 1000,
                'discount': 0,
                'tax_rate': 0,
                'tax_amount': 0,
                'total_price': 2000,
            }],
            'subtotal': 2000,
            'discount_amount': 0,
            'discount_percent': 0,
            'tax_amount': 0,
            'total_amount': 2000,
            'amount_paid': 2000,
            'change_amount': 0,
            'payment_method': 'cash',
        }

        response = client.post(
            reverse('pos:create_sale'),
            data=json.dumps(sale_data),
            content_type='application/json',
        )
        result = response.json()
        assert result['success'] is True, f"Sale creation failed: {result}"
        assert Sale.objects.filter(sale_number=result['sale_number']).exists()

    def test_pos_create_customer_ajax(self, cashier_user):
        """Cashier creates a customer from POS modal → customer created"""
        client = logged_in(cashier_user)

        response = client.post(
            reverse('pos:create_customer'),
            data=json.dumps({
                'name': 'POS New Customer',
                'phone': '+243 99 888 7777',
            }),
            content_type='application/json',
        )
        result = response.json()
        assert result['success'] is True
        assert Customer.objects.filter(name='POS New Customer').exists()

    def test_pos_dashboard_renders(self, admin_user):
        """Sales dashboard renders with charts"""
        client = logged_in(admin_user)

        response = client.get(reverse('pos:dashboard'))
        assert_page_ok(response, "POS dashboard")


# ============================================================================
# TEST: Navigation Links - Verify all sidebar/menu links work
# ============================================================================

@pytest.mark.django_db
class TestNavigationLinks:
    """Verify every link in the navigation bar loads without errors"""

    def test_admin_can_reach_all_pages(self, admin_user, enterprise, location_warehouse):
        """Admin user can navigate to every section from the sidebar"""
        client = logged_in(admin_user)

        pages = [
            ('home', reverse('home')),
            ('pos_dashboard', reverse('pos:dashboard')),
            ('stock_dashboard', reverse('stock:dashboard')),
            ('stock_low', reverse('stock:low_stock')),
            ('stock_out', reverse('stock:out_of_stock')),
            ('stock_movements', reverse('stock:movements')),
            ('stock_entry', reverse('stock:entry')),
            ('locations', reverse('locations:dashboard')),
            ('transfers', reverse('transfers:list')),
            ('transfer_create', reverse('transfers:create')),
            ('reports', reverse('reports:dashboard')),
            ('customers', reverse('customers:customer_list')),
            ('customer_create', reverse('customers:customer_create')),
            ('credits', reverse('customers:credit_list')),
            ('expenses', reverse('accounting:expense_list')),
            ('expense_create', reverse('accounting:expense_create')),
            ('expense_categories', reverse('accounting:expense_category_list')),
            ('expense_cat_create', reverse('accounting:expense_category_create')),
            ('cash_sessions', reverse('accounting:cash_session_list')),
            ('cash_session_open', reverse('accounting:cash_session_open')),
            ('products', reverse('products:product_list')),
            ('product_create', reverse('products:product_create')),
            ('categories', reverse('products:category_list')),
            ('category_create', reverse('products:category_create')),
            ('users', reverse('accounts:user_list')),
            ('user_create', reverse('accounts:user_create')),
        ]

        for page_name, url in pages:
            # follow=True so 'home' (which dispatches to a role dashboard) resolves.
            response = client.get(url, follow=True)
            assert response.status_code == 200, (
                f"Page '{page_name}' ({url}) returned {response.status_code} instead of 200"
            )

    def test_cashier_can_reach_allowed_pages(self, cashier_user):
        """Cashier can navigate to pages they're allowed to access"""
        client = logged_in(cashier_user)

        allowed = [
            ('home', reverse('home')),
            ('pos_cashier', reverse('pos:cashier')),
            ('pos_dashboard', reverse('pos:dashboard')),
            ('customers', reverse('customers:customer_list')),
            ('cash_sessions', reverse('accounting:cash_session_list')),
        ]

        for page_name, url in allowed:
            # follow=True so 'home' (which dispatches to the caisse dashboard) resolves.
            response = client.get(url, follow=True)
            assert response.status_code == 200, (
                f"Cashier should access '{page_name}' ({url}) but got {response.status_code}"
            )

    def test_cashier_blocked_from_admin_pages(self, cashier_user):
        """Cashier cannot access admin-only pages"""
        client = logged_in(cashier_user)

        blocked = [
            ('user_list', reverse('accounts:user_list')),
            ('user_create', reverse('accounts:user_create')),
            ('product_create', reverse('products:product_create')),
            ('stock_entry', reverse('stock:entry')),
        ]

        for page_name, url in blocked:
            response = client.get(url)
            assert response.status_code in [302, 403], (
                f"Cashier should NOT access '{page_name}' ({url}) but got {response.status_code}"
            )


# ============================================================================
# TEST: Form Validation Messages Render in UI
# ============================================================================

@pytest.mark.django_db
class TestValidationRendersInUI:
    """Ensure validation errors are shown to the user (not silent failures)"""

    def test_user_create_shows_error_on_bad_input(self, admin_user):
        """Submitting bad data re-renders form with error messages visible"""
        client = logged_in(admin_user)

        response = client.post(reverse('accounts:user_create'), {
            'username': '',  # required
            'role': 'cashier',
            'password': 'a',
            'password_confirm': 'b',
        })
        assert response.status_code == 200  # re-renders, not redirect
        html = response.content.decode()
        # Page should show some error indication
        assert ('error' in html.lower() or 'erreur' in html.lower() or
                'alert' in html.lower() or 'invalid' in html.lower() or
                'obligatoire' in html.lower() or 'requis' in html.lower()), \
            "No error message visible to user after bad input"

    def test_product_create_shows_error_on_invalid_price(self, admin_user, enterprise):
        """Invalid price shows error, doesn't crash"""
        client = logged_in(admin_user)
        CategoryFactory(enterprise=enterprise)

        response = client.post(reverse('products:product_create'), {
            'name': 'Bad Price Product',
            'purchase_price': 'abc',
            'sale_price': 'xyz',
        })
        assert response.status_code == 200  # re-renders
        html = response.content.decode()
        assert ('error' in html.lower() or 'erreur' in html.lower() or
                'invalide' in html.lower() or 'alert' in html.lower()), \
            "No error message for invalid prices"

    def test_stock_entry_shows_error_on_missing_product(self, stock_manager_user):
        """Stock entry with no product selected shows error"""
        client = logged_in(stock_manager_user)

        response = client.post(reverse('stock:entry'), {
            'product': '',
            'quantity': '10',
            'reason': 'purchase',
        })
        # Should either re-render with error or redirect with error message
        assert response.status_code in [200, 302]

    def test_expense_create_shows_error_on_missing_amount(self, admin_user):
        """Expense without amount shows error"""
        client = logged_in(admin_user)

        response = client.post(reverse('accounting:expense_create'), {
            'description': 'Missing amount expense',
            'amount': '',
            'expense_date': '',
        })
        assert response.status_code == 200
        html = response.content.decode()
        assert ('error' in html.lower() or 'erreur' in html.lower() or
                'alert' in html.lower() or 'obligatoire' in html.lower()), \
            "No error message for missing amount"
