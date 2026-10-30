from django.db.models import QuerySet


class EnterpriseQuerySetMixin:
    """
    Mixin to filter querysets by enterprise based on the current user.
    """

    # Rôle : limite un queryset à l'entreprise de l'utilisateur ; tout pour un superuser, rien pour les autres cas.
    # Liens : appelée par EnterpriseViewSetMixin.get_queryset et LocationViewSetMixin.get_queryset de ce fichier.
    def get_enterprise_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Filter queryset by user's enterprise.
        """
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        # Superusers can see all
        if user.is_superuser:
            return queryset

        # Filter by user's enterprise
        if hasattr(user, 'enterprise') and user.enterprise:
            return queryset.filter(enterprise=user.enterprise)

        return queryset.none()


class LocationQuerySetMixin:
    """
    Mixin to filter querysets by location based on the current user.
    """

    # Rôle : limite un queryset à l'emplacement de l'utilisateur ; superuser et owner voient toute l'entreprise.
    # Liens : appelée par LocationViewSetMixin.get_queryset, mixin qu'aucune vue n'utilise aujourd'hui.
    def get_location_queryset(self, queryset: QuerySet) -> QuerySet:
        """
        Filter queryset by user's assigned location(s).
        """
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        # Superusers and owners can see all within enterprise
        if user.is_superuser or user.role == 'owner':
            if hasattr(user, 'enterprise') and user.enterprise:
                return queryset.filter(enterprise=user.enterprise)
            return queryset

        # Managers and below see only their location
        if hasattr(user, 'location') and user.location:
            return queryset.filter(location=user.location)

        return queryset.none()


class EnterpriseViewSetMixin(EnterpriseQuerySetMixin):
    """
    Mixin for ViewSets that automatically filters by enterprise
    and sets enterprise on object creation.
    """

    # Rôle : ajoute automatiquement le filtre par entreprise au queryset du ViewSet.
    # Liens : appelée par DRF ; TransferViewSet (api/v1/views/transfers.py), LocationViewSet et LocationStockViewSet
    # (api/v1/views/locations.py) l'héritent ; les vues qui la surchargent l'appellent via super().
    def get_queryset(self):
        queryset = super().get_queryset()
        return self.get_enterprise_queryset(queryset)

    # Rôle : enregistre le nouvel objet avec l'entreprise de l'utilisateur, si celui-ci en a une.
    # Liens : appelée par DRF pour TransferViewSet et LocationStockViewSet ; LocationViewSet a sa propre version.
    def perform_create(self, serializer):
        """
        Automatically set enterprise when creating objects.
        """
        user = self.request.user
        if hasattr(user, 'enterprise') and user.enterprise:
            serializer.save(enterprise=user.enterprise)
        else:
            serializer.save()


class LocationViewSetMixin(LocationQuerySetMixin, EnterpriseQuerySetMixin):
    """
    Mixin for ViewSets that filters by both enterprise and location.
    """

    # Rôle : filtre le queryset par entreprise, puis par emplacement.
    # Liens : appelle get_enterprise_queryset et get_location_queryset ; aucune vue n'hérite de ce mixin.
    def get_queryset(self):
        queryset = super().get_queryset()
        # First filter by enterprise
        queryset = self.get_enterprise_queryset(queryset)
        # Then filter by location if applicable
        return self.get_location_queryset(queryset)

    # Rôle : enregistre le nouvel objet avec l'entreprise et l'emplacement de l'utilisateur, s'ils existent.
    # Liens : prévue pour DRF ; aucune vue n'hérite de ce mixin aujourd'hui.
    def perform_create(self, serializer):
        """
        Automatically set enterprise and location when creating objects.
        """
        user = self.request.user
        extra_kwargs = {}

        if hasattr(user, 'enterprise') and user.enterprise:
            extra_kwargs['enterprise'] = user.enterprise

        if hasattr(user, 'location') and user.location:
            extra_kwargs['location'] = user.location

        serializer.save(**extra_kwargs)


class AuditCreateMixin:
    """
    Mixin to automatically set created_by on object creation.
    """

    # Rôle : enregistre le nouvel objet en renseignant created_by avec l'utilisateur connecté.
    # Liens : prévue pour DRF ; hérité seulement par AuditMixin de ce fichier, aucune vue ne l'utilise aujourd'hui.
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AuditUpdateMixin:
    """
    Mixin to automatically set updated_by on object update.
    """

    # Rôle : enregistre la modification en renseignant updated_by avec l'utilisateur connecté.
    # Liens : prévue pour DRF ; hérité seulement par AuditMixin de ce fichier, aucune vue ne l'utilise aujourd'hui.
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AuditMixin(AuditCreateMixin, AuditUpdateMixin):
    """
    Combined mixin for both create and update auditing.
    """
    pass
