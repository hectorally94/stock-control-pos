"""
Factory classes for creating test data using factory_boy
"""
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import User, ActionLog
from apps.products.models import Category, Product, ProductPackaging
from apps.stock.models import Stock, StockMovement
from apps.customers.models import Customer, CustomerCredit, CreditPayment
from apps.pos.models import Sale, SaleItem
from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession, DailySummary
from apps.settings.models import StoreSetting

fake = Faker('fr_FR')


# ============================================================================
# ACCOUNTS
# ============================================================================

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name', locale='fr_FR')
    last_name = factory.Faker('last_name', locale='fr_FR')
    phone = factory.Faker('phone_number', locale='fr_FR')
    role = 'cashier'
    is_active = True
    is_staff = False
    is_superuser = False
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if create:
            obj.set_password(extracted or 'password123')
            obj.save()


class ActionLogFactory(DjangoModelFactory):
    class Meta:
        model = ActionLog
    
    user = factory.SubFactory(UserFactory)
    action_type = factory.Iterator(['create', 'update', 'delete', 'login', 'logout'])
    entity_type = factory.Iterator(['product', 'sale', 'stock', 'customer'])
    entity_id = factory.Faker('random_int', min=1, max=1000)
    description = factory.Faker('sentence', locale='fr_FR')
    ip_address = factory.Faker('ipv4')


# ============================================================================
# PRODUCTS
# ============================================================================

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'Catégorie {n}')
    description = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product
        django_get_or_create = ('name',)
    
    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f'Produit {n}')
    description = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    barcode = factory.Sequence(lambda n: f'BAR{n:010d}')
    sku = factory.Sequence(lambda n: f'SKU{n:06d}')
    unit = factory.Iterator(['piece', 'kg', 'liter', 'carton'])
    purchase_price = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=100, max_value=50000)
    sale_price = factory.LazyAttribute(lambda obj: obj.purchase_price * Decimal('1.3'))
    tax_rate = Decimal('0.00')
    min_stock_threshold = factory.Faker('random_int', min=5, max=20)
    is_popular = False
    is_active = True


class ProductPackagingFactory(DjangoModelFactory):
    class Meta:
        model = ProductPackaging
    
    product = factory.SubFactory(ProductFactory)
    name = factory.Iterator(['Carton', 'Pack', 'Palette'])
    barcode = factory.Sequence(lambda n: f'PKG{n:010d}')
    quantity = factory.Faker('random_int', min=6, max=24)
    is_active = True


# ============================================================================
# STOCK
# ============================================================================

class StockFactory(DjangoModelFactory):
    class Meta:
        model = Stock
        django_get_or_create = ('product',)
    
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=1, max_value=1000)
    last_restock_date = factory.Faker('date_time_this_month', tzinfo=timezone.get_current_timezone())


class StockMovementFactory(DjangoModelFactory):
    class Meta:
        model = StockMovement
    
    product = factory.SubFactory(ProductFactory)
    user = factory.SubFactory(UserFactory)
    movement_type = factory.Iterator(['entry', 'exit'])
    reason = factory.LazyAttribute(lambda obj: 'purchase' if obj.movement_type == 'entry' else 'sale')
    quantity = factory.Faker('pydecimal', left_digits=3, right_digits=2, positive=True, min_value=1, max_value=100)
    unit_cost = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=100, max_value=50000)
    reference = factory.Sequence(lambda n: f'REF-{n:06d}')
    notes = factory.Faker('sentence', locale='fr_FR')


# ============================================================================
# CUSTOMERS
# ============================================================================

class CustomerFactory(DjangoModelFactory):
    class Meta:
        model = Customer
        django_get_or_create = ('phone',)
    
    name = factory.Faker('name', locale='fr_FR')
    phone = factory.Faker('phone_number', locale='fr_FR')
    email = factory.Faker('email', locale='fr_FR')
    address = factory.Faker('address', locale='fr_FR')
    credit_limit = Decimal('100000.00')
    current_balance = Decimal('0.00')
    total_purchases = Decimal('0.00')
    purchase_count = 0
    loyalty_points = 0
    is_active = True


class CustomerCreditFactory(DjangoModelFactory):
    class Meta:
        model = CustomerCredit
    
    customer = factory.SubFactory(CustomerFactory)
    sale = None  # Will be set when creating with sale
    original_amount = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=1000, max_value=50000)
    remaining_amount = factory.LazyAttribute(lambda obj: obj.original_amount)
    due_date = factory.Faker('date_between', start_date='+1d', end_date='+30d')
    status = 'pending'
    notes = factory.Faker('sentence', locale='fr_FR')


class CreditPaymentFactory(DjangoModelFactory):
    class Meta:
        model = CreditPayment
    
    credit = factory.SubFactory(CustomerCreditFactory)
    user = factory.SubFactory(UserFactory)
    amount = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=100, max_value=10000)
    payment_method = factory.Iterator(['cash', 'mobile_money', 'card'])
    reference = factory.Sequence(lambda n: f'PAY-{n:06d}')
    notes = factory.Faker('sentence', locale='fr_FR')


# ============================================================================
# POS
# ============================================================================

class SaleFactory(DjangoModelFactory):
    class Meta:
        model = Sale
    
    sale_number = factory.Sequence(lambda n: f'VNT-TEST-{n:08d}')
    customer = factory.SubFactory(CustomerFactory)
    user = factory.SubFactory(UserFactory, role='cashier')
    subtotal = Decimal('0.00')
    discount_amount = Decimal('0.00')
    discount_percent = Decimal('0.00')
    tax_amount = Decimal('0.00')
    total_amount = Decimal('0.00')
    amount_paid = Decimal('0.00')
    change_amount = Decimal('0.00')
    payment_method = factory.Iterator(['cash', 'mobile_money', 'card', 'credit'])
    status = 'completed'


class SaleItemFactory(DjangoModelFactory):
    class Meta:
        model = SaleItem
    
    sale = factory.SubFactory(SaleFactory)
    product = factory.SubFactory(ProductFactory)
    product_name = factory.LazyAttribute(lambda obj: obj.product.name)
    quantity = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True, min_value=1, max_value=10)
    unit_price = factory.LazyAttribute(lambda obj: obj.product.sale_price)
    purchase_price = factory.LazyAttribute(lambda obj: obj.product.purchase_price)
    discount_amount = Decimal('0.00')
    tax_rate = Decimal('0.00')
    tax_amount = Decimal('0.00')
    total_price = factory.LazyAttribute(lambda obj: obj.unit_price * obj.quantity - obj.discount_amount)


# ============================================================================
# ACCOUNTING
# ============================================================================

class ExpenseCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ExpenseCategory
        django_get_or_create = ('name',)
    
    name = factory.Sequence(lambda n: f'Catégorie Dépense {n}')
    description = factory.Faker('text', max_nb_chars=200, locale='fr_FR')
    is_active = True


class ExpenseFactory(DjangoModelFactory):
    class Meta:
        model = Expense
    
    expense_category = factory.SubFactory(ExpenseCategoryFactory)
    user = factory.SubFactory(UserFactory)
    description = factory.Faker('sentence', locale='fr_FR')
    amount = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=1000, max_value=100000)
    expense_date = factory.Faker('date_this_month')
    payment_method = factory.Iterator(['cash', 'mobile_money', 'card', 'bank_transfer'])
    supplier = factory.Faker('company', locale='fr_FR')
    reference = factory.Sequence(lambda n: f'EXP-{n:06d}')
    is_recurring = False
    notes = factory.Faker('sentence', locale='fr_FR')


class CashRegisterSessionFactory(DjangoModelFactory):
    class Meta:
        model = CashRegisterSession
    
    user = factory.SubFactory(UserFactory, role='cashier')
    opening_balance = factory.Faker('pydecimal', left_digits=6, right_digits=2, positive=True, min_value=10000, max_value=50000)
    closing_balance = Decimal('0.00')
    expected_balance = Decimal('0.00')
    difference = Decimal('0.00')
    status = 'open'
    notes = factory.Faker('sentence', locale='fr_FR')


class DailySummaryFactory(DjangoModelFactory):
    class Meta:
        model = DailySummary
        django_get_or_create = ('summary_date',)
    
    summary_date = factory.Faker('date_this_month')
    total_sales = factory.Faker('pydecimal', left_digits=7, right_digits=2, positive=True, min_value=50000, max_value=500000)
    total_expenses = factory.Faker('pydecimal', left_digits=6, right_digits=2, positive=True, min_value=10000, max_value=100000)
    total_cash = factory.LazyAttribute(lambda obj: obj.total_sales * Decimal('0.6'))
    total_mobile_money = factory.LazyAttribute(lambda obj: obj.total_sales * Decimal('0.3'))
    total_card = factory.LazyAttribute(lambda obj: obj.total_sales * Decimal('0.1'))
    total_credit = Decimal('0.00')
    credit_collected = Decimal('0.00')
    total_cost_of_goods = factory.LazyAttribute(lambda obj: obj.total_sales * Decimal('0.7'))
    gross_profit = factory.LazyAttribute(lambda obj: obj.total_sales - obj.total_cost_of_goods)
    number_of_sales = factory.Faker('random_int', min=10, max=100)
    number_of_customers = factory.Faker('random_int', min=5, max=50)
    net_profit = factory.LazyAttribute(lambda obj: obj.gross_profit - obj.total_expenses)


# ============================================================================
# SETTINGS
# ============================================================================

class StoreSettingFactory(DjangoModelFactory):
    class Meta:
        model = StoreSetting
        django_get_or_create = ('key',)
    
    key = factory.Sequence(lambda n: f'setting_key_{n}')
    value = factory.Faker('word')
    description = factory.Faker('sentence', locale='fr_FR')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_complete_sale(user=None, customer=None, num_items=3):
    """Create a complete sale with items"""
    if user is None:
        user = UserFactory(role='cashier')
    if customer is None:
        customer = CustomerFactory()
    
    sale = SaleFactory(user=user, customer=customer)
    
    subtotal = Decimal('0.00')
    for _ in range(num_items):
        product = ProductFactory()
        StockFactory(product=product, quantity=Decimal('100.00'))
        
        item = SaleItemFactory(sale=sale, product=product)
        subtotal += item.total_price
    
    sale.subtotal = subtotal
    sale.total_amount = subtotal
    sale.amount_paid = subtotal
    sale.save()
    
    return sale


def create_stock_with_movements(product=None, num_movements=5):
    """Create stock with movement history"""
    if product is None:
        product = ProductFactory()
    
    stock = StockFactory(product=product, quantity=Decimal('0.00'))
    
    for _ in range(num_movements):
        movement = StockMovementFactory(product=product)
        if movement.movement_type == 'entry':
            stock.quantity += movement.quantity
        else:
            stock.quantity -= movement.quantity
    
    stock.save()
    return stock

