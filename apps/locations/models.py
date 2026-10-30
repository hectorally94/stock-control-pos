from django.db import models
from django.conf import settings


class LocationType(models.Model):
    """
    User-manageable label for an emplacement type (e.g. "Boutique",
    "Dépôt (Warehouse)", "Pharmacie", "Entrepôt Froid").

    Each type maps to a BEHAVIOUR (warehouse or boutique) so the core logic
    (transfers, dashboard sections) keeps working regardless of the label.
    """

    BEHAVIOUR_CHOICES = [
        ('warehouse', 'Dépôt (Warehouse)'),
        ('boutique', 'Boutique'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='location_types',
        verbose_name='Entreprise'
    )
    name = models.CharField(max_length=100, verbose_name='Nom du type')
    behaviour = models.CharField(
        max_length=20,
        choices=BEHAVIOUR_CHOICES,
        default='boutique',
        verbose_name='Comportement',
        help_text="Détermine comment le type se comporte (dépôt qui approvisionne, ou boutique qui vend)."
    )
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')

    class Meta:
        db_table = 'location_types'
        verbose_name = "Type d'emplacement"
        verbose_name_plural = "Types d'emplacement"
        ordering = ['enterprise', 'name']
        unique_together = [['enterprise', 'name']]

    def __str__(self):
        return self.name


class Location(models.Model):
    """
    Location model representing warehouses and boutiques.
    Each location belongs to an enterprise and has a specific type.
    """

    LOCATION_TYPE_CHOICES = [
        ('warehouse', 'Dépôt (Warehouse)'),
        ('boutique', 'Boutique'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='locations',
        verbose_name='Entreprise'
    )
    name = models.CharField(max_length=255, verbose_name='Nom')
    code = models.CharField(max_length=50, verbose_name='Code',
                           help_text='Code unique pour cet emplacement')
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        verbose_name='Comportement',
        help_text="Comportement interne (dépôt/boutique), dérivé du type choisi."
    )
    type_ref = models.ForeignKey(
        LocationType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locations',
        verbose_name='Type'
    )
    address = models.TextField(blank=True, null=True, verbose_name='Adresse')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Téléphone')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_locations',
        verbose_name='Responsable'
    )
    is_main_warehouse = models.BooleanField(
        default=False,
        verbose_name='Dépôt principal',
        help_text='Marquer comme dépôt principal de l\'entreprise'
    )
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_locations',
        verbose_name='Créé par'
    )

    class Meta:
        db_table = 'locations'
        verbose_name = 'Emplacement'
        verbose_name_plural = 'Emplacements'
        ordering = ['enterprise', 'location_type', 'name']
        unique_together = [['enterprise', 'code']]
        indexes = [
            models.Index(fields=['enterprise', 'location_type'], name='idx_loc_enterprise_type'),
            models.Index(fields=['is_active'], name='idx_loc_active'),
            models.Index(fields=['code'], name='idx_loc_code'),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"

    def save(self, *args, **kwargs):
        # Ensure only one main warehouse per enterprise
        if self.is_main_warehouse:
            Location.objects.filter(
                enterprise=self.enterprise,
                is_main_warehouse=True
            ).exclude(pk=self.pk).update(is_main_warehouse=False)
        super().save(*args, **kwargs)

    @property
    def is_warehouse(self):
        return self.location_type == 'warehouse'

    @property
    def is_boutique(self):
        return self.location_type == 'boutique'

    @property
    def type_display(self):
        """Custom type label if set, otherwise the built-in behaviour label."""
        if self.type_ref_id:
            return self.type_ref.name
        return self.get_location_type_display()


class LocationStock(models.Model):
    """
    Stock levels per location per product.
    This enables multi-location inventory tracking.
    """

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='stock_items',
        verbose_name='Emplacement'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='location_stocks',
        verbose_name='Produit'
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        verbose_name='Quantité'
    )
    min_stock_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        default=0,
        verbose_name='Seuil minimum'
    )
    max_stock_threshold = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name='Seuil maximum'
    )
    last_restock_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Dernier réapprovisionnement'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')

    class Meta:
        db_table = 'location_stocks'
        verbose_name = 'Stock par emplacement'
        verbose_name_plural = 'Stocks par emplacement'
        unique_together = [['location', 'product']]
        indexes = [
            models.Index(fields=['location', 'product'], name='idx_locstock_loc_prod'),
            models.Index(fields=['quantity'], name='idx_locstock_qty'),
        ]

    def __str__(self):
        return f"{self.product.name} @ {self.location.name}: {self.quantity}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0
