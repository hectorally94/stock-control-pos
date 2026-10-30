from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    """
    Permission for admin, owner and manager roles.
    Full access to all operations.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager']


class IsStockManager(permissions.BasePermission):
    """
    Permission for stock manager role.
    Can only access stock-related operations.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager']


class IsCashier(permissions.BasePermission):
    """
    Permission for cashier role.
    Can access POS operations and read customer info.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner', 'manager', 'boutique_manager', 'cashier']


class IsAccountant(permissions.BasePermission):
    """
    Permission for accountant role.
    Read-only access to all models for reports.
    """

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

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role in ['admin', 'owner']


class RoleBasedPermission(permissions.BasePermission):
    """
    Dynamic role-based permission.
    Define allowed roles in the view.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Get allowed roles from view
        allowed_roles = getattr(view, 'allowed_roles', ['admin', 'owner'])

        # Check if user's role is in allowed roles
        return request.user.role in allowed_roles
