from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with role-based access control"""

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('owner', 'Owner (Propriétaire)'),
        ('manager', 'Manager (Gérant)'),
        ('warehouse_manager', 'Warehouse Manager (Gestionnaire Dépôt)'),
        ('boutique_manager', 'Boutique Manager (Gestionnaire Boutique)'),
        ('stock_manager', 'Stock Manager (Gestionnaire de stock)'),
        ('cashier', 'Cashier (Caissier)'),
        ('accountant', 'Accountant (Comptable/Auditeur)'),
    ]

    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Phone')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, verbose_name='Role')
    enterprise = models.ForeignKey(
        'core.Enterprise',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Entreprise'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_users',
        verbose_name='Emplacement assigné'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role'], name='idx_users_role'),
            models.Index(fields=['email'], name='idx_users_email'),
        ]
    
    # Rôle : affiche l'utilisateur sous la forme « nom complet (libellé du rôle) ».
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


class ActionLog(models.Model):
    """Audit trail for all important actions"""
    
    ACTION_TYPE_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='action_logs', verbose_name='User')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES, verbose_name='Action Type')
    entity_type = models.CharField(max_length=50, verbose_name='Entity Type')
    entity_id = models.BigIntegerField(blank=True, null=True, verbose_name='Entity ID')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    old_value = models.TextField(blank=True, null=True, verbose_name='Old Value (JSON)', help_text='Previous value in JSON format')
    new_value = models.TextField(blank=True, null=True, verbose_name='New Value (JSON)', help_text='New value in JSON format')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Address')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        db_table = 'action_logs'
        verbose_name = 'Action Log'
        verbose_name_plural = 'Action Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='idx_action_logs_user'),
            models.Index(fields=['entity_type', 'entity_id'], name='idx_action_logs_entity'),
            models.Index(fields=['created_at'], name='idx_action_logs_date'),
            models.Index(fields=['action_type'], name='idx_action_logs_type'),
        ]
    
    # Rôle : résume une entrée du journal : utilisateur, action, type d'entité et date.
    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.entity_type} ({self.created_at})"
