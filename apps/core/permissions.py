from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission for enterprise owners - full access to their enterprise.
    """

    # Rôle : autorise seulement un utilisateur connecté de rôle owner.
    # Liens : importée par api/v1/views/core.py mais absente de ses permission_classes ; aucune vue ne l'utilise.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'owner'
        )


class IsWarehouseManager(permissions.BasePermission):
    """
    Permission for warehouse managers - can manage stock, transfers, products.
    """

    # Rôle : autorise les rôles owner et warehouse_manager.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'warehouse_manager']
        )


class IsBoutiqueManager(permissions.BasePermission):
    """
    Permission for boutique managers - can manage their location's sales, staff.
    """

    # Rôle : autorise les rôles owner et boutique_manager.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'boutique_manager']
        )


class IsCashier(permissions.BasePermission):
    """
    Permission for cashiers - POS operations only.
    """

    # Rôle : autorise owner, boutique_manager et cashier.
    # Liens : non utilisée ; les vues API importent l'IsCashier de api/v1/permissions.py, une classe distincte.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'boutique_manager', 'cashier']
        )


class IsManager(permissions.BasePermission):
    """
    Permission for any manager role (warehouse or boutique).
    """

    # Rôle : autorise owner, manager, warehouse_manager et boutique_manager.
    # Liens : appelée par DRF pour LocationViewSet (api/v1/views/locations.py).
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class IsStaffOrOwner(permissions.BasePermission):
    """
    Permission for staff members or enterprise owners.
    """

    # Rôle : autorise un compte is_staff ou de rôle owner.
    # Liens : appelée par DRF pour le ViewSet des entreprises (api/v1/views/core.py).
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or request.user.role == 'owner')
        )


class CanManageStock(permissions.BasePermission):
    """
    Permission to manage stock operations (entry, exit, adjustments).
    """

    # Rôle : autorise owner, manager, warehouse_manager et stock_manager.
    # Liens : appelée par DRF pour LocationStockViewSet (api/v1/views/locations.py).
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'stock_manager']
        )


class CanManageTransfers(permissions.BasePermission):
    """
    Permission to manage inter-location transfers.
    """

    # Rôle : autorise owner, manager, warehouse_manager et boutique_manager.
    # Liens : appelée par DRF pour TransferViewSet et TransferItemViewSet (api/v1/views/transfers.py).
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class CanReceiveTransfers(permissions.BasePermission):
    """
    Permission to receive transfers at a location.
    """

    # Rôle : autorise owner, manager, warehouse_manager et boutique_manager à recevoir un transfert.
    # Liens : appelée par DRF sur une action POST de TransferViewSet (api/v1/views/transfers.py).
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager']
        )


class CanManageSales(permissions.BasePermission):
    """
    Permission to manage sales (create, void).
    """

    # Rôle : autorise owner, manager, boutique_manager et cashier.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'boutique_manager', 'cashier']
        )


class CanViewReports(permissions.BasePermission):
    """
    Permission to view reports and analytics.
    """

    # Rôle : autorise owner, manager, warehouse_manager, boutique_manager et accountant.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'manager', 'warehouse_manager', 'boutique_manager', 'accountant']
        )


class CanManageUsers(permissions.BasePermission):
    """
    Permission to manage users within the enterprise.
    """

    # Rôle : autorise les rôles owner et admin.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ['owner', 'admin']
        )


class ReadOnly(permissions.BasePermission):
    """
    Read-only access for safe methods.
    """

    # Rôle : autorise seulement les méthodes sûres (GET, HEAD, OPTIONS), sans vérifier la connexion.
    # Liens : appelée par DRF si la classe est déclarée ; aucune vue ne l'utilise aujourd'hui.
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
