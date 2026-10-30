"""
Pytest configuration and fixtures

The test database is SQLite in-memory, configured in stock_control.settings_test
(DJANGO_SETTINGS_MODULE in pytest.ini), so the suite never needs a MySQL server.
"""
import pytest
from rest_framework.test import APIClient
from tests.factories import *  # noqa: F401,F403


# Prépare un client API DRF sans authentification, base des autres clients de test.
# Liens : rest_framework.test.APIClient, utilisé par les tests de l'API /api/v1/.
@pytest.fixture
def api_client():
    """DRF API client"""
    return APIClient()


# ============================================================================
# FACTORY FIXTURES
# ============================================================================

# Prépare l'accès à UserFactory pour créer des utilisateurs dans les tests.
# Liens : tests/factories.py (UserFactory), apps/accounts/models.py
@pytest.fixture
def user_factory():
    return UserFactory


# Prépare l'accès à CategoryFactory pour créer des catégories dans les tests.
# Liens : tests/factories.py (CategoryFactory), apps/products/models.py
@pytest.fixture
def category_factory():
    return CategoryFactory


# Prépare l'accès à ProductFactory pour créer des produits dans les tests.
# Liens : tests/factories.py (ProductFactory), apps/products/models.py
@pytest.fixture
def product_factory():
    return ProductFactory


# Prépare l'accès à StockFactory pour créer des lignes de stock dans les tests.
# Liens : tests/factories.py (StockFactory), apps/stock/models.py
@pytest.fixture
def stock_factory():
    return StockFactory


# Prépare l'accès à CustomerFactory pour créer des clients dans les tests.
# Liens : tests/factories.py (CustomerFactory), apps/customers/models.py
@pytest.fixture
def customer_factory():
    return CustomerFactory


# Prépare l'accès à SaleFactory pour créer des ventes dans les tests.
# Liens : tests/factories.py (SaleFactory), apps/pos/models.py
@pytest.fixture
def sale_factory():
    return SaleFactory


# Prépare l'accès à ExpenseFactory pour créer des dépenses dans les tests.
# Liens : tests/factories.py (ExpenseFactory), apps/accounting/models.py
@pytest.fixture
def expense_factory():
    return ExpenseFactory


# ============================================================================
# USER FIXTURES
# ============================================================================

# Prépare un utilisateur de rôle admin.
# Liens : fixture user_factory, modèle User de apps/accounts/models.py
@pytest.fixture
def admin_user(user_factory):
    """Admin user"""
    return user_factory(role='admin')


# Prépare un utilisateur de rôle manager.
# Liens : fixture user_factory, modèle User de apps/accounts/models.py
@pytest.fixture
def manager_user(user_factory):
    """Manager user"""
    return user_factory(role='manager')


# Prépare un utilisateur de rôle cashier (caissier).
# Liens : fixture user_factory, modèle User de apps/accounts/models.py
@pytest.fixture
def cashier_user(user_factory):
    """Cashier user"""
    return user_factory(role='cashier')


# Prépare un utilisateur de rôle stock_manager.
# Liens : fixture user_factory, modèle User de apps/accounts/models.py
@pytest.fixture
def stock_manager_user(user_factory):
    """Stock manager user"""
    return user_factory(role='stock_manager')


# Prépare un utilisateur de rôle accountant (comptable).
# Liens : fixture user_factory, modèle User de apps/accounts/models.py
@pytest.fixture
def accountant_user(user_factory):
    """Accountant user"""
    return user_factory(role='accountant')


# ============================================================================
# AUTHENTICATED CLIENT FIXTURES
# ============================================================================

# Prépare un client API déjà authentifié avec un utilisateur admin.
# Liens : fixtures api_client et admin_user, permissions de api/v1/permissions.py
@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Authenticated API client with admin user"""
    api_client.force_authenticate(user=admin_user)
    return api_client


# Prépare un client API authentifié avec le rôle admin.
# Liens : fixtures api_client et admin_user, permissions de api/v1/permissions.py
@pytest.fixture
def admin_client(api_client, admin_user):
    """Admin authenticated client"""
    api_client.force_authenticate(user=admin_user)
    return api_client


# Prépare un client API authentifié avec le rôle manager.
# Liens : fixtures api_client et manager_user, permissions de api/v1/permissions.py
@pytest.fixture
def manager_client(api_client, manager_user):
    """Manager authenticated client"""
    api_client.force_authenticate(user=manager_user)
    return api_client


# Prépare un client API authentifié avec le rôle cashier.
# Liens : fixtures api_client et cashier_user, permissions de api/v1/permissions.py
@pytest.fixture
def cashier_client(api_client, cashier_user):
    """Cashier authenticated client"""
    api_client.force_authenticate(user=cashier_user)
    return api_client


# Prépare un client API authentifié avec le rôle stock_manager.
# Liens : fixtures api_client et stock_manager_user, permissions de api/v1/permissions.py
@pytest.fixture
def stock_manager_client(api_client, stock_manager_user):
    """Stock manager authenticated client"""
    api_client.force_authenticate(user=stock_manager_user)
    return api_client

