"""
Signals for POS app - Auto stock updates on sale
"""
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from apps.pos.models import Sale, SaleItem
from apps.stock.models import StockMovement
from apps.accounts.models import ActionLog


@receiver(post_save, sender=SaleItem)
def create_stock_movement_on_sale_item(sender, instance, created, **kwargs):
    """
    Automatically create stock movement when a sale item is created.
    This ensures stock is decremented immediately when items are added to a completed sale.
    """

    # Only process new items for completed sales
    if created and instance.sale.status == 'completed':
        StockMovement.objects.create(
            enterprise=instance.sale.enterprise,
            location=instance.sale.location,
            product=instance.product,
            user=instance.sale.user,
            movement_type='exit',
            reason='sale',
            quantity=instance.quantity,
            reference=instance.sale.sale_number,
            notes=f'Vente automatique: {instance.sale.sale_number}'
        )


@receiver(post_save, sender=Sale)
def handle_sale_status_changes(sender, instance, created, **kwargs):
    """
    Handle sale status changes (cancellation, refund).
    
    - On sale cancellation: Create entry movements to return stock
    - On sale refund: Create entry movements with customer_return reason
    """
    
    # Only handle status changes (not on creation)
    if not created:
        # Get the old status from the pre_save signal
        old_status = getattr(instance, '_original_status', None)
        
        # If sale was completed and now cancelled, reverse stock
        if old_status == 'completed' and instance.status == 'cancelled':
            with transaction.atomic():
                # Create reverse entry movements
                for item in instance.items.all():
                    StockMovement.objects.create(
                        enterprise=instance.enterprise,
                        location=instance.location,
                        product=item.product,
                        user=instance.user,
                        movement_type='entry',
                        reason='correction',
                        quantity=item.quantity,
                        reference=f'CANCEL-{instance.sale_number}',
                        notes=f'Annulation de vente: {instance.sale_number}'
                    )

        # If sale was completed and now refunded, return stock
        elif old_status == 'completed' and instance.status == 'refunded':
            with transaction.atomic():
                # Create entry movements for customer return
                for item in instance.items.all():
                    StockMovement.objects.create(
                        enterprise=instance.enterprise,
                        location=instance.location,
                        product=item.product,
                        user=instance.user,
                        movement_type='entry',
                        reason='customer_return',
                        quantity=item.quantity,
                        reference=f'REFUND-{instance.sale_number}',
                        notes=f'Remboursement de vente: {instance.sale_number}'
                    )


@receiver(pre_save, sender=Sale)
def store_original_sale_status(sender, instance, **kwargs):
    """
    Store the original status before saving to track changes.
    This helps us detect status transitions in post_save.
    """
    if instance.pk:
        try:
            instance._original_status = Sale.objects.get(pk=instance.pk).status
        except Sale.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=Sale)
def log_sale_action(sender, instance, created, **kwargs):
    """
    Log sale creation/modification to ActionLog for audit trail.
    """
    if created:
        ActionLog.objects.create(
            user=instance.user,
            action_type='create',
            entity_type='sale',
            entity_id=instance.id,
            description=f'Vente créée: {instance.sale_number} - {instance.total_amount} FB',
            new_value=f'{{"sale_number": "{instance.sale_number}", "total_amount": "{instance.total_amount}", "payment_method": "{instance.payment_method}"}}'
        )
    else:
        # Check if status changed
        if hasattr(instance, '_original_status') and instance._original_status != instance.status:
            ActionLog.objects.create(
                user=instance.user,
                action_type='update',
                entity_type='sale',
                entity_id=instance.id,
                description=f'Statut de vente modifié: {instance.sale_number}',
                old_value=f'{{"status": "{instance._original_status}"}}',
                new_value=f'{{"status": "{instance.status}"}}'
            )

