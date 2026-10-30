from django.db import models
from django.conf import settings


class ExpenseCategory(models.Model):
    """Expense categories"""

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expense_categories',
        verbose_name='Entreprise'
    )
    name = models.CharField(max_length=100, verbose_name='Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        db_table = 'expense_categories'
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'
        unique_together = [['enterprise', 'name']]
        indexes = [
            models.Index(fields=['name'], name='idx_expense_categories_name'),
            models.Index(fields=['enterprise'], name='idx_expense_cat_enterprise'),
        ]

    # Rôle : renvoie le nom de la catégorie comme libellé de l'objet.
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Business expenses"""

    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Emplacement'
    )
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, blank=True, null=True, related_name='expenses', verbose_name='Category')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='expenses', verbose_name='User')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Amount')
    description = models.TextField(verbose_name='Description')
    expense_date = models.DateField(verbose_name='Expense Date')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, verbose_name='Payment Method')
    reference = models.CharField(max_length=100, blank=True, null=True, verbose_name='Reference', help_text='Receipt/invoice number')
    supplier = models.CharField(max_length=200, blank=True, null=True, verbose_name='Supplier/Vendor')
    is_recurring = models.BooleanField(default=False, verbose_name='Recurring Expense')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'expenses'
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        ordering = ['-expense_date']
        indexes = [
            models.Index(fields=['expense_category'], name='idx_expenses_category'),
            models.Index(fields=['expense_date'], name='idx_expenses_date'),
            models.Index(fields=['user'], name='idx_expenses_user'),
            models.Index(fields=['enterprise'], name='idx_expenses_enterprise'),
            models.Index(fields=['location'], name='idx_expenses_location'),
        ]

    # Rôle : renvoie un libellé « description - montant FB (date) ».
    def __str__(self):
        return f"{self.description} - {self.amount} FB ({self.expense_date})"


class CashRegisterSession(models.Model):
    """Cash register opening/closing sessions"""

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cash_sessions',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cash_sessions',
        verbose_name='Emplacement'
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, related_name='cash_sessions', verbose_name='Cashier')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Opening Balance')
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Closing Balance')
    expected_balance = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Expected Balance')
    difference = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Difference')
    opened_at = models.DateTimeField(verbose_name='Opened At')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='Closed At')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='Status')
    notes = models.TextField(blank=True, null=True, verbose_name='Notes')

    class Meta:
        db_table = 'cash_register_sessions'
        verbose_name = 'Cash Register Session'
        verbose_name_plural = 'Cash Register Sessions'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['user'], name='idx_cash_sessions_user'),
            models.Index(fields=['opened_at'], name='idx_cash_sessions_date'),
            models.Index(fields=['status'], name='idx_cash_sessions_status'),
            models.Index(fields=['enterprise'], name='idx_cash_sess_enterprise'),
            models.Index(fields=['location'], name='idx_cash_sess_location'),
        ]

    # Rôle : renvoie un libellé avec l'utilisateur, la date d'ouverture et le statut de la session.
    def __str__(self):
        return f"{self.user.username} - {self.opened_at.strftime('%Y-%m-%d %H:%M')} ({self.status})"


class DailySummary(models.Model):
    """Daily financial summaries (auto-generated)"""

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_summaries',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_summaries',
        verbose_name='Emplacement'
    )
    summary_date = models.DateField(verbose_name='Date')
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Total Sales')
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Total Expenses')
    total_cash = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Cash Payments')
    total_mobile_money = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Mobile Money Payments')
    total_card = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Card Payments')
    total_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Credit Sales')
    credit_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Credit Collected')
    total_cost_of_goods = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Cost of Goods')
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Gross Profit')
    number_of_sales = models.IntegerField(default=0, verbose_name='Number of Sales')
    number_of_customers = models.IntegerField(default=0, verbose_name='Number of Customers')
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Net Profit')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'daily_summaries'
        verbose_name = 'Daily Summary'
        verbose_name_plural = 'Daily Summaries'
        ordering = ['-summary_date']
        unique_together = [['enterprise', 'location', 'summary_date']]
        indexes = [
            models.Index(fields=['summary_date'], name='idx_daily_summaries_date'),
            models.Index(fields=['enterprise'], name='idx_daily_summ_enterprise'),
            models.Index(fields=['location'], name='idx_daily_summ_location'),
        ]

    # Rôle : renvoie un libellé avec la date du résumé et le bénéfice net.
    def __str__(self):
        return f"Summary for {self.summary_date}: {self.net_profit} FB profit"
