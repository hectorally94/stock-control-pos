from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission for enterprise owners - full access to their enterprise.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'owner'
        )


class IsWarehouseManager(permissions.BasePermission):
    """
    Permission for warehouse managers - can manage stock, transfers, products.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'warehouse_manager']
        )


class IsBoutiqueManager(permissions.BasePermission):
    """
    Permission for boutique managers - can manage their location's sales, staff.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'boutique_manager']
        )


class IsCashier(permissions.BasePermission):
    """
    Permission for cashiers - POS operations only.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'boutique_manager', 'cashier']
        )


class IsManager(permissions.BasePermission):
    """
    Permission for any manager role (warehouse or boutique).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class IsStaffOrOwner(permissions.BasePermission):
    """
    Permission for staff members or enterprise owners.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or request.user.role == 'owner')
        )


class CanManageStock(permissions.BasePermission):
    """
    Permission to manage stock operations (entry, exit, adjustments).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'stock_manager']
        )


class CanManageTransfers(permissions.BasePermission):
    """
    Permission to manage inter-location transfers.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class CanReceiveTransfers(permissions.BasePermission):
    """
    Permission to receive transfers at a location.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class CanManageSales(permissions.BasePermission):
    """
    Permission to manage sales (create, void).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'boutique_manager', 'cashier']
        )


class CanViewReports(permissions.BasePermission):
    """
    Permission to view reports and analytics.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager', 'accountant']
        )


class CanManageUsers(permissions.BasePermission):
    """
    Permission to manage users within the enterprise.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'admin']
        )


class ReadOnly(permissions.BasePermission):
    """
    Read-only access for safe methods.
    """

    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
