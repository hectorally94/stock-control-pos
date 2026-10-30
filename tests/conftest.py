"""
Pytest configuration and fixtures

The test database is SQLite in-memory, configured in stock_control.settings_test
(DJANGO_SETTINGS_MODULE in pytest.ini), so the suite never needs a MySQL server.
"""
import pytest
from rest_framework.test import APIClient
from tests.factories import *  # noqa: F401,F403


@pytest.fixture
def api_client():
    """DRF API client"""
    return APIClient()


# ============================================================================
# FACTORY FIXTURES
# ============================================================================

@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def category_factory():
    return CategoryFactory


@pytest.fixture
def product_factory():
    return ProductFactory


@pytest.fixture
def stock_factory():
    return StockFactory


@pytest.fixture
def customer_factory():
    return CustomerFactory


@pytest.fixture
def sale_factory():
    return SaleFactory


@pytest.fixture
def expense_factory():
    return ExpenseFactory


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture
def admin_user(user_factory):
    """Admin user"""
    return user_factory(role='admin')


@pytest.fixture
def manager_user(user_factory):
    """Manager user"""
    return user_factory(role='manager')


@pytest.fixture
def cashier_user(user_factory):
    """Cashier user"""
    return user_factory(role='cashier')


@pytest.fixture
def stock_manager_user(user_factory):
    """Stock manager user"""
    return user_factory(role='stock_manager')


@pytest.fixture
def accountant_user(user_factory):
    """Accountant user"""
    return user_factory(role='accountant')


# ============================================================================
# AUTHENTICATED CLIENT FIXTURES
# ============================================================================

@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Authenticated API client with admin user"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Admin authenticated client"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def manager_client(api_client, manager_user):
    """Manager authenticated client"""
    api_client.force_authenticate(user=manager_user)
    return api_client


@pytest.fixture
def cashier_client(api_client, cashier_user):
    """Cashier authenticated client"""
    api_client.force_authenticate(user=cashier_user)
    return api_client


@pytest.fixture
def stock_manager_client(api_client, stock_manager_user):
    """Stock manager authenticated client"""
    api_client.force_authenticate(user=stock_manager_user)
    return api_client

