from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Transfer(models.Model):
    """
    Inter-location stock transfer.
    Tracks transfers from warehouse to boutique or between locations.
    """

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('in_transit', 'En transit'),
        ('received', 'Reçu'),
        ('cancelled', 'Annulé'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name='Entreprise'
    )
    reference = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Référence',
        help_text='Numéro unique de transfert'
    )
    source_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='outgoing_transfers',
        verbose_name='Emplacement source'
    )
    destination_location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='incoming_transfers',
        verbose_name='Emplacement destination'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Statut'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')

    # Tracking dates
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Envoyé le')
    received_at = models.DateTimeField(null=True, blank=True, verbose_name='Reçu le')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Annulé le')

    # User tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_transfers',
        verbose_name='Créé par'
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_transfers',
        verbose_name='Envoyé par'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_transfers',
        verbose_name='Reçu par'
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_transfers',
        verbose_name='Annulé par'
    )
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Raison d\'annulation'
    )

    class Meta:
        db_table = 'transfers'
        verbose_name = 'Transfert'
        verbose_name_plural = 'Transferts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['enterprise', 'status'], name='idx_transfer_ent_status'),
            models.Index(fields=['source_location'], name='idx_transfer_source'),
            models.Index(fields=['destination_location'], name='idx_transfer_dest'),
            models.Index(fields=['reference'], name='idx_transfer_ref'),
            models.Index(fields=['created_at'], name='idx_transfer_created'),
        ]

    def __str__(self):
        return f"{self.reference}: {self.source_location.name} → {self.destination_location.name}"

    def clean(self):
        if self.source_location == self.destination_location:
            raise ValidationError('La source et la destination doivent être différentes.')
        if self.source_location.enterprise != self.destination_location.enterprise:
            raise ValidationError('Les emplacements doivent appartenir à la même entreprise.')

    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate reference: TRF-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            last_transfer = Transfer.objects.filter(
                reference__startswith=f'TRF-{today}'
            ).order_by('-reference').first()

            if last_transfer:
                last_num = int(last_transfer.reference.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            self.reference = f'TRF-{today}-{new_num:04d}'

        super().save(*args, **kwargs)

    def send(self, user):
        """Mark the transfer as sent/in transit.

        Records an EXIT stock movement at the source for each item; via
        StockMovement.save() this keeps BOTH the Stock and LocationStock tables
        in sync (single source of truth).
        """
        if self.status not in ['draft', 'pending']:
            raise ValidationError('Seuls les transferts en brouillon ou en attente peuvent être envoyés.')

        from apps.locations.models import LocationStock
        from apps.stock.models import StockMovement

        # Availability check first (per-location source stock).
        for item in self.items.all():
            stock = LocationStock.objects.filter(
                location=self.source_location, product=item.product
            ).first()
            available = stock.quantity if stock else 0
            if available < item.quantity:
                raise ValidationError(
                    f'Stock insuffisant pour {item.product.name}. '
                    f'Disponible: {available}, Demandé: {item.quantity}'
                )

        # Deduct from source via stock movements.
        for item in self.items.all():
            StockMovement.objects.create(
                enterprise=self.enterprise,
                location=self.source_location,
                product=item.product,
                user=user,
                movement_type='exit',
                reason='transfer_out',
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                reference=self.reference,
                notes=f'Transfert sortant vers {self.destination_location.name}',
            )

        self.status = 'in_transit'
        self.sent_at = timezone.now()
        self.sent_by = user
        self.save()

    def receive(self, user):
        """Mark the transfer as received; records ENTRY movements at destination."""
        if self.status != 'in_transit':
            raise ValidationError('Seuls les transferts en transit peuvent être reçus.')

        from apps.stock.models import StockMovement

        for item in self.items.all():
            qty = item.received_quantity or item.quantity
            StockMovement.objects.create(
                enterprise=self.enterprise,
                location=self.destination_location,
                product=item.product,
                user=user,
                movement_type='entry',
                reason='transfer_in',
                quantity=qty,
                unit_cost=item.unit_cost,
                reference=self.reference,
                notes=f'Transfert entrant depuis {self.source_location.name}',
            )

        self.status = 'received'
        self.received_at = timezone.now()
        self.received_by = user
        self.save()

    def cancel(self, user, reason):
        """Cancel the transfer; returns goods to source if already in transit."""
        if self.status in ['received', 'cancelled']:
            raise ValidationError('Ce transfert ne peut pas être annulé.')

        from apps.stock.models import StockMovement

        if self.status == 'in_transit':
            for item in self.items.all():
                StockMovement.objects.create(
                    enterprise=self.enterprise,
                    location=self.source_location,
                    product=item.product,
                    user=user,
                    movement_type='entry',
                    reason='correction',
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    reference=self.reference,
                    notes=f'Annulation transfert {self.reference}',
                )

        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancellation_reason = reason
        self.save()

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_quantity(self):
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class TransferItem(models.Model):
    """
    Individual item in a transfer.
    """

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Transfert'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='transfer_items',
        verbose_name='Produit'
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        verbose_name='Quantité envoyée'
    )
    received_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name='Quantité reçue',
        help_text='Laisser vide si identique à la quantité envoyée'
    )
    unit_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Coût unitaire'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')

    class Meta:
        db_table = 'transfer_items'
        verbose_name = 'Article de transfert'
        verbose_name_plural = 'Articles de transfert'
        unique_together = [['transfer', 'product']]
        indexes = [
            models.Index(fields=['transfer', 'product'], name='idx_transitem_transfer_prod'),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def variance(self):
        """Difference between sent and received quantity."""
        if self.received_quantity is not None:
            return self.received_quantity - self.quantity
        return 0

    @property
    def total_cost(self):
        if self.unit_cost:
            return self.quantity * self.unit_cost
        return None
