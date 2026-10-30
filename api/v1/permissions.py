from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission for admin, owner and manager roles.
    Full access to all operations.
    """

    # Rôle : autorise uniquement les utilisateurs connectés de rôle admin, owner ou manager.
    # Liens : appelée par DRF ; utilisée dans la plupart des fichiers de api/v1/views/ (accounts, pos, settings...).
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager']


class IsStockManager(permissions.BasePermission):
    """
    Permission for stock manager role.
    Can only access stock-related operations.
    """

    # Rôle : autorise admin, owner, manager et les trois rôles de gestion de stock ou de boutique.
    # Liens : appelée par DRF ; utilisée par StockViewSet et StockMovementViewSet (api/v1/views/stock.py).
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']


class IsCashier(permissions.BasePermission):
    """
    Permission for cashier role.
    Can access POS operations and read customer info.
    """

    # Rôle : autorise cashier, boutique_manager, manager, owner et admin ; les autres rôles sont refusés.
    # Liens : appelée par DRF ; utilisée dans api/v1/views/pos.py et api/v1/views/customers.py.
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier']


class IsAccountant(permissions.BasePermission):
    """
    Permission for accountant role.
    Read-only access to all models for reports.
    """

    # Rôle : donne la lecture seule à accountant et l'accès complet à admin, owner et manager ; refuse les autres.
    # Liens : appelée par DRF ; utilisée dans api/v1/views/accounting.py et api/v1/views/products.py.
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Accountants have read-only access
        if request.user.role == 'accountant':
            return request.method in permissions.SAFE_METHODS

        # Admin, owner and manager have full access
        return request.user.role in ['admin', 'owner', 'manager']


class IsAdminOnly(permissions.BasePermission):
    """
    Permission for admin and owner only.
    Used for user management and sensitive operations.
    """

    # Rôle : autorise uniquement les utilisateurs connectés de rôle admin ou owner.
    # Liens : appelée par DRF ; utilisée par UserViewSet (api/v1/views/accounts.py).
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner']


class RoleBasedPermission(permissions.BasePermission):
    """
    Dynamic role-based permission.
    Define allowed roles in the view.
    """

    # Rôle : compare le rôle de l'utilisateur à view.allowed_roles, ou à admin et owner si l'attribut est absent.
    # Liens : appelée par DRF si une vue la déclare ; aucune vue du projet ne l'utilise actuellement.
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Get allowed roles from view
        allowed_roles = getattr(view, 'allowed_roles', ['admin', 'owner'])

        # Check if user's role is in allowed roles
        return request.user.role in allowed_roles
