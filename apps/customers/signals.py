"""
Signals for Customers app - Auto balance and statistics tracking
"""
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from apps.customers.models import Customer, CustomerCredit
from apps.pos.models import Sale
from apps.settings.models import StoreSetting


# Rôle : à la création d'une vente terminée, met à jour les totaux et points ; à crédit, crée le CustomerCredit.
# Liens : signal post_save de Sale (apps/pos/models.py) ; lit StoreSetting ; écrit Customer et CustomerCredit.
# Vente passée de completed à cancelled ou refunded : inverse ces effets et solde le crédit restant.
@receiver(post_save, sender=Sale)
def update_customer_on_sale(sender, instance, created, **kwargs):
    """
    Update customer statistics and create credit record when a sale is created.
    
    For all sales:
    - Update total_purchases
    - Update purchase_count
    - Update loyalty_points (if enabled)
    
    For credit sales:
    - Create CustomerCredit record
    - Update current_balance
    - Validate credit limit
    """
    
    # Only process if customer exists and sale is completed
    if not instance.customer or instance.status != 'completed':
        return
    
    customer = instance.customer
    
    if created:
        with transaction.atomic():
            # Update customer statistics
            from decimal import Decimal
            customer.total_purchases = Decimal(str(customer.total_purchases)) + Decimal(str(instance.total_amount))
            customer.purchase_count += 1
            
            # Update loyalty points if enabled
            loyalty_enabled = StoreSetting.get_setting('loyalty_program_enabled', 'false')
            if loyalty_enabled.lower() == 'true':
                try:
                    loyalty_rate = int(StoreSetting.get_setting('loyalty_points_rate', '1000'))
                    # Award 1 point per loyalty_rate FB spent
                    points_earned = int(instance.total_amount / loyalty_rate)
                    customer.loyalty_points += points_earned
                except (ValueError, ZeroDivisionError):
                    pass  # Skip if settings are invalid
            
            # Handle credit sales
            if instance.payment_method == 'credit':
                credit_amount = Decimal(str(instance.total_amount)) - Decimal(str(instance.amount_paid))
                
                # Validate credit limit
                new_balance = Decimal(str(customer.current_balance)) + credit_amount
                if new_balance > customer.credit_limit:
                    raise ValidationError(
                        f'Limite de crédit dépassée. Limite: {customer.credit_limit} FB, '
                        f'Nouveau solde: {new_balance} FB'
                    )
                
                # Create CustomerCredit record
                CustomerCredit.objects.create(
                    customer=customer,
                    sale=instance,
                    original_amount=credit_amount,
                    remaining_amount=credit_amount,
                    status='pending'
                )
                
                # Update customer balance
                customer.current_balance = Decimal(str(customer.current_balance)) + credit_amount
            
            customer.save()
    
    # Handle sale status changes (not on creation)
    if not created:
        # Get original status
        original_status = getattr(instance, '_original_status', None)
        
        # If sale was completed and now cancelled or refunded
        if original_status == 'completed' and instance.status in ['cancelled', 'refunded']:
            with transaction.atomic():
                # Reverse customer statistics
                from decimal import Decimal
                customer.total_purchases = Decimal(str(customer.total_purchases)) - Decimal(str(instance.total_amount))
                customer.purchase_count -= 1
                
                # Reverse loyalty points if enabled
                loyalty_enabled = StoreSetting.get_setting('loyalty_program_enabled', 'false')
                if loyalty_enabled.lower() == 'true':
                    try:
                        loyalty_rate = int(StoreSetting.get_setting('loyalty_points_rate', '1000'))
                        points_to_remove = int(instance.total_amount / loyalty_rate)
                        customer.loyalty_points = max(0, customer.loyalty_points - points_to_remove)
                    except (ValueError, ZeroDivisionError):
                        pass
                
                # If sale had credit, mark as paid and reduce balance
                try:
                    credit = instance.credit
                    if credit.status != 'paid':
                        customer.current_balance = Decimal(str(customer.current_balance)) - Decimal(str(credit.remaining_amount))
                        if customer.current_balance < 0:
                            customer.current_balance = Decimal('0')
                        credit.status = 'paid'
                        credit.remaining_amount = 0
                        credit.save()
                except CustomerCredit.DoesNotExist:
                    pass
                
                customer.save()


# Rôle : garde dans instance._original_status le statut en base, avant l'enregistrement de la vente.
# Liens : signal pre_save de Sale ; lu par update_customer_on_sale ; équivalent dans apps/pos/signals.py.
@receiver(pre_save, sender=Sale)
def store_original_sale_status_for_customer(sender, instance, **kwargs):
    """
    Store the original status before saving to track changes.
    This is used in the post_save signal to detect status transitions.
    """
    if instance.pk:
        try:
            instance._original_status = Sale.objects.get(pk=instance.pk).status
        except Sale.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


# Rôle : lève ValidationError si un client existant a une limite de crédit inférieure à son solde.
# Liens : signal pre_save de Customer, déclenché par customer_edit, CreditPayment.save, update_customer_on_sale.
@receiver(pre_save, sender=Customer)
def validate_customer_credit_limit(sender, instance, **kwargs):
    """
    Ensure credit limit is not reduced below current balance.
    """
    if instance.pk:
        try:
            old_customer = Customer.objects.get(pk=instance.pk)
            if instance.credit_limit < instance.current_balance:
                raise ValidationError(
                    f'La limite de crédit ({instance.credit_limit} FB) ne peut pas être '
                    f'inférieure au solde actuel ({instance.current_balance} FB)'
                )
        except Customer.DoesNotExist:
            pass

