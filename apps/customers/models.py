from django.db import models
from django.conf import settings


class Customer(models.Model):
    """Customer database"""

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='customers',
        verbose_name='Entreprise'
    )
    name = models.CharField(max_length=200, verbose_name='Name')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Phone')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    address = models.TextField(blank=True, null=True, verbose_name='Address')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Credit Limit')
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Current Balance')
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Total Purchases')
    purchase_count = models.IntegerField(default=0, verbose_name='Purchase Count')
    loyalty_points = models.IntegerField(default=0, verbose_name='Loyalty Points')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        indexes = [
            models.Index(fields=['name'], name='idx_customers_name'),
            models.Index(fields=['phone'], name='idx_customers_phone'),
            models.Index(fields=['current_balance'], name='idx_customers_balance'),
            models.Index(fields=['total_purchases'], name='idx_customers_purchases'),
            models.Index(fields=['enterprise'], name='idx_customers_enterprise'),
        ]
    
    # Rôle : renvoie le nom et le téléphone du client, ou « No phone » à défaut.
    def __str__(self):
        return f"{self.name} ({self.phone or 'No phone'})"
    
    # Rôle : indique si le client a une dette, c'est-à-dire un current_balance supérieur à 0.
    # Liens : exposée par api/v1/serializers/customers.py ; vérifiée par tests/test_models.py.
    @property
    def has_outstanding_credit(self):
        """Check if customer has unpaid credit"""
        return self.current_balance > 0


class CustomerCredit(models.Model):
    """Customer credit/debt tracking"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='credits', verbose_name='Customer')
    sale = models.OneToOneField('pos.Sale', on_delete=models.RESTRICT, related_name='credit', verbose_name='Sale')
    original_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Original Amount')
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Remaining Amount')
    due_date = models.DateField(blank=True, null=True, verbose_name='Due Date')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        db_table = 'customer_credits'
        verbose_name = 'Customer Credit'
        verbose_name_plural = 'Customer Credits'
        indexes = [
            models.Index(fields=['customer'], name='idx_customer_credits_customer'),
            models.Index(fields=['status'], name='idx_customer_credits_status'),
            models.Index(fields=['sale'], name='idx_customer_credits_sale'),
            models.Index(fields=['due_date'], name='idx_customer_credits_due_date'),
        ]
    
    # Rôle : renvoie le client, le montant restant dû et le statut du crédit.
    def __str__(self):
        return f"{self.customer.name} - {self.remaining_amount} FB (Status: {self.status})"
    
    # Rôle : indique si l'échéance est dépassée alors que le crédit n'est pas soldé ; faux sans échéance.
    # Liens : action overdue de api/v1/views/customers.py, api/v1/serializers/customers.py, apps/customers/admin.py.
    # Sert aussi à l'affichage dans credit_list.html, customer_detail.html et record_payment.html.
    @property
    def is_overdue(self):
        """Check if credit is overdue"""
        from datetime import date
        return self.due_date and self.due_date < date.today() and self.status != 'paid'


class CreditPayment(models.Model):
    """Payments toward customer credits"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
    ]
    
    credit = models.ForeignKey(CustomerCredit, on_delete=models.CASCADE, related_name='payments', verbose_name='Credit')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='credit_payments', verbose_name='User')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Amount')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='Payment Method')
    payment_reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Payment Reference')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        db_table = 'credit_payments'
        verbose_name = 'Credit Payment'
        verbose_name_plural = 'Credit Payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['credit'], name='idx_credit_payments_credit'),
            models.Index(fields=['created_at'], name='idx_credit_payments_date'),
            models.Index(fields=['user'], name='idx_credit_payments_user'),
        ]
    
    # Rôle : renvoie le client, le montant et la date du paiement.
    def __str__(self):
        return f"{self.credit.customer.name} - {self.amount} FB ({self.created_at.strftime('%Y-%m-%d')})"
    
    # Rôle : à la création seulement, déduit le paiement du crédit (statut partial ou paid) et du solde client.
    # Liens : appelée via record_payment (apps/customers/views.py) et la route API /api/v1/credit-payments/.
    # Son customer.save() déclenche validate_customer_credit_limit (apps/customers/signals.py).
    def save(self, *args, **kwargs):
        """Update credit remaining amount when payment is recorded"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update credit remaining amount
            credit = self.credit
            credit.remaining_amount -= self.amount
            if credit.remaining_amount <= 0:
                credit.status = 'paid'
                credit.remaining_amount = 0
            elif credit.remaining_amount < credit.original_amount:
                credit.status = 'partial'
            credit.save()
            
            # Update customer current balance
            customer = credit.customer
            customer.current_balance -= self.amount
            if customer.current_balance < 0:
                customer.current_balance = 0
            customer.save()
