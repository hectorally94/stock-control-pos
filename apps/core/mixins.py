from django.db.models import QuerySet


class EnterpriseQuerySetMixin:
    """
    Mixin to filter querysets by enterprise based on the current user.
    """

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

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.get_enterprise_queryset(queryset)

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

    def get_queryset(self):
        queryset = super().get_queryset()
        # First filter by enterprise
        queryset = self.get_enterprise_queryset(queryset)
        # Then filter by location if applicable
        return self.get_location_queryset(queryset)

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

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AuditUpdateMixin:
    """
    Mixin to automatically set updated_by on object update.
    """

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class AuditMixin(AuditCreateMixin, AuditUpdateMixin):
    """
    Combined mixin for both create and update auditing.
    """
    pass
