from django.db import models
from django.conf import settings


class Sale(models.Model):
    """Sales transactions"""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
        ('credit', 'Credit'),
    ]

    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Emplacement'
    )
    sale_number = models.CharField(max_length=50, unique=True, verbose_name='Sale Number', help_text='e.g., VNT-20251204-0001')
    customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, blank=True, null=True, related_name='sales', verbose_name='Customer')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='sales', verbose_name='Cashier')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Subtotal')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Discount Amount')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Discount %')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Tax Amount')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Amount')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Amount Paid')
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Change')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='Payment Method')
    payment_reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Payment Reference')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name='Status')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Sale Date')

    class Meta:
        db_table = 'sales'
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer'], name='idx_sales_customer'),
            models.Index(fields=['user'], name='idx_sales_user'),
            models.Index(fields=['created_at'], name='idx_sales_date'),
            models.Index(fields=['sale_number'], name='idx_sales_number'),
            models.Index(fields=['status'], name='idx_sales_status'),
            models.Index(fields=['payment_method'], name='idx_sales_payment'),
            models.Index(fields=['enterprise'], name='idx_sales_enterprise'),
            models.Index(fields=['location'], name='idx_sales_location'),
        ]
    
    def __str__(self):
        return f"{self.sale_number} - {self.total_amount} FB"
    
    @classmethod
    def generate_sale_number(cls):
        """Generate unique sale number: VNT-YYYYMMDD-NNNN"""
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        prefix = f"VNT-{today}-"
        
        # Get last sale number for today
        last_sale = cls.objects.filter(sale_number__startswith=prefix).order_by('-sale_number').first()
        
        if last_sale:
            last_num = int(last_sale.sale_number.split('-')[-1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        return f"{prefix}{new_num:04d}"


class SaleItem(models.Model):
    """Items in each sale"""
    
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items', verbose_name='Sale')
    product = models.ForeignKey('products.Product', on_delete=models.RESTRICT, related_name='sale_items', verbose_name='Product')
    product_name = models.CharField(max_length=200, verbose_name='Product Name', help_text='Snapshot at time of sale')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='Quantity')
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Unit Price', help_text='Sale price at time of sale')
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Purchase Price', help_text='For profit calculation')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Discount Amount')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Tax Rate %')
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Tax Amount')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Line Total')
    
    class Meta:
        db_table = 'sale_items'
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
        indexes = [
            models.Index(fields=['sale'], name='idx_sale_items_sale'),
            models.Index(fields=['product'], name='idx_sale_items_product'),
        ]
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    @property
    def profit(self):
        """Calculate profit for this line item"""
        return (self.unit_price - self.purchase_price) * self.quantity
