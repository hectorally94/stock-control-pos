from django.db import models
from django.conf import settings


class Stock(models.Model):
    """Current stock levels per product (aggregate across locations)"""

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stocks',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stocks',
        verbose_name='Emplacement'
    )
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='stock_info', verbose_name='Product')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0, verbose_name='Quantity')
    last_restock_date = models.DateField(blank=True, null=True, verbose_name='Last Restock Date')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'stock'
        verbose_name = 'Stock'
        verbose_name_plural = 'Stock'
        indexes = [
            models.Index(fields=['product'], name='idx_stock_product'),
            models.Index(fields=['enterprise'], name='idx_stock_enterprise'),
            models.Index(fields=['location'], name='idx_stock_location'),
        ]

    def __str__(self):
        location_str = f" @ {self.location.name}" if self.location else ""
        return f"{self.product.name}{location_str}: {self.quantity} {self.product.unit}"

    @property
    def is_low_stock(self):
        """Check if stock is below minimum threshold"""
        return self.quantity <= self.product.min_stock_threshold


class StockMovement(models.Model):
    """Stock movement history (entries and exits)"""

    MOVEMENT_TYPE_CHOICES = [
        ('entry', 'Entry'),
        ('exit', 'Exit'),
    ]

    REASON_ENTRY_CHOICES = [
        ('purchase', 'Purchase'),
        ('customer_return', 'Customer Return'),
        ('correction', 'Correction'),
        ('initial_stock', 'Initial Stock'),
        ('transfer_in', 'Transfer In'),
        ('other_entry', 'Other Entry'),
    ]

    REASON_EXIT_CHOICES = [
        ('sale', 'Sale (POS)'),
        ('manual_sale', 'Manual Sale (Outside POS)'),
        ('loss', 'Loss'),
        ('breakage', 'Breakage'),
        ('expiration', 'Expiration'),
        ('correction', 'Correction'),
        ('transfer_out', 'Transfer Out'),
        ('other_exit', 'Other Exit'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name='Emplacement'
    )
    product = models.ForeignKey('products.Product', on_delete=models.RESTRICT, related_name='movements', verbose_name='Product')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='stock_movements', verbose_name='User')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES, verbose_name='Movement Type')
    reason = models.CharField(max_length=50, verbose_name='Reason')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='Quantity', help_text='Always positive')
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Unit Cost', help_text='For entries')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Reference', help_text='e.g., Invoice number')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        db_table = 'stock_movements'
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product'], name='idx_stock_movements_product'),
            models.Index(fields=['created_at'], name='idx_stock_movements_date'),
            models.Index(fields=['movement_type'], name='idx_stock_movements_type'),
            models.Index(fields=['user'], name='idx_stock_movements_user'),
            models.Index(fields=['reason'], name='idx_stock_movements_reason'),
            models.Index(fields=['enterprise'], name='idx_stock_mvmt_enterprise'),
            models.Index(fields=['location'], name='idx_stock_mvmt_location'),
        ]

    def __str__(self):
        location_str = f" @ {self.location.name}" if self.location else ""
        return f"{self.movement_type.upper()}: {self.product.name}{location_str} - {self.quantity} ({self.reason})"

    def save(self, *args, **kwargs):
        """Update stock quantity when movement is created.

        A movement is the single source of truth: it updates BOTH the aggregate
        `Stock` table and the per-location `LocationStock` table so every
        dashboard (stock, locations, reports) stays consistent.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if not is_new:
            return

        delta = self.quantity if self.movement_type == 'entry' else -self.quantity

        # 1) Aggregate Stock table (product [+ location] [+ enterprise]).
        stock_filters = {'product': self.product}
        if self.location:
            stock_filters['location'] = self.location
        if self.enterprise:
            stock_filters['enterprise'] = self.enterprise

        stock, _ = Stock.objects.get_or_create(**stock_filters, defaults={'quantity': 0})
        stock.quantity = (stock.quantity or 0) + delta
        if self.movement_type == 'entry':
            stock.last_restock_date = self.created_at.date()
        stock.save()

        # 2) Per-location LocationStock table (keeps locations dashboard +
        #    reports in sync with sales/entries, not just transfers).
        if self.location:
            from apps.locations.models import LocationStock
            loc_stock, _ = LocationStock.objects.get_or_create(
                location=self.location,
                product=self.product,
                defaults={'quantity': 0},
            )
            loc_stock.quantity = (loc_stock.quantity or 0) + delta
            if self.movement_type == 'entry':
                loc_stock.last_restock_date = self.created_at
            loc_stock.save()
