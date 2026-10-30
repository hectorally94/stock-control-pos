from django.db import models


class Category(models.Model):
    """Product categories"""

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name='Entreprise'
    )
    name = models.CharField(max_length=100, verbose_name='Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'categories'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = [['enterprise', 'name']]
        indexes = [
            models.Index(fields=['name'], name='idx_categories_name'),
            models.Index(fields=['enterprise'], name='idx_categories_enterprise'),
        ]

    # Rôle : renvoie le nom de la catégorie comme libellé de l'objet.
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product catalog"""

    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('sachet', 'Sachet'),
        ('carton', 'Carton'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
    ]

    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Entreprise'
    )
    category = models.ForeignKey(Category, on_delete=models.RESTRICT, related_name='products', verbose_name='Category')
    name = models.CharField(max_length=200, verbose_name='Name')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    barcode = models.CharField(max_length=50, blank=True, null=True, verbose_name='Barcode')
    sku = models.CharField(max_length=50, blank=True, null=True, verbose_name='SKU')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, verbose_name='Unit')
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Purchase Price')
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Sale Price')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Tax Rate (%)')
    min_stock_threshold = models.IntegerField(default=0, verbose_name='Minimum Stock Threshold')
    is_popular = models.BooleanField(default=False, verbose_name='Popular (Show in POS quick buttons)')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Image')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['category'], name='idx_products_category'),
            models.Index(fields=['barcode'], name='idx_products_barcode'),
            models.Index(fields=['name'], name='idx_products_name'),
            models.Index(fields=['enterprise'], name='idx_products_enterprise'),
        ]

    # Rôle : renvoie le nom du produit suivi de son code-barres ou, à défaut, de son SKU.
    def __str__(self):
        return f"{self.name} ({self.barcode or self.sku})"

    # Rôle : calcule la marge en % par rapport au prix d'achat ; renvoie 0 si ce prix est nul.
    # Liens : api/v1/serializers/products.py, apps/products/admin.py, product_list.html et product_detail.html.
    # Même formule que updateMargin dans apps/products/templates/products/product_form.html.
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.purchase_price > 0:
            return ((self.sale_price - self.purchase_price) / self.purchase_price) * 100
        return 0


class ProductPackaging(models.Model):
    """Product packaging conversions (e.g., 1 carton = 12 units)"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packagings', verbose_name='Product')
    name = models.CharField(max_length=50, verbose_name='Packaging Name', help_text='e.g., Carton, Pack')
    quantity_per_unit = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='Quantity per Unit', help_text='e.g., 12 for 1 carton = 12 pieces')
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name='Barcode')
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name='Sale Price', help_text='Optional special price for this packaging')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        db_table = 'product_packagings'
        verbose_name = 'Product Packaging'
        verbose_name_plural = 'Product Packagings'
        indexes = [
            models.Index(fields=['product'], name='idx_product_packagings_product'),
            models.Index(fields=['barcode'], name='idx_product_packagings_barcode'),
        ]
    
    # Rôle : renvoie le produit, le nom du conditionnement et le nombre d'unités qu'il contient.
    def __str__(self):
        return f"{self.product.name} - {self.name} ({self.quantity_per_unit} units)"
