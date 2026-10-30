from django.db import models
from django.conf import settings


class Enterprise(models.Model):
    """
    Enterprise model for multi-enterprise support.
    Each enterprise represents a business entity with multiple locations.
    """

    name = models.CharField(max_length=255, verbose_name='Nom')
    code = models.CharField(max_length=50, unique=True, verbose_name='Code',
                           help_text='Code unique pour identifier l\'entreprise')
    address = models.TextField(blank=True, null=True, verbose_name='Adresse')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Téléphone')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='NIF/ID Fiscal')
    logo = models.ImageField(upload_to='enterprises/logos/', blank=True, null=True, verbose_name='Logo')
    currency = models.CharField(max_length=10, default='FB', verbose_name='Devise')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_enterprises',
        verbose_name='Créé par'
    )

    class Meta:
        db_table = 'enterprises'
        verbose_name = 'Entreprise'
        verbose_name_plural = 'Entreprises'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code'], name='idx_enterprise_code'),
            models.Index(fields=['is_active'], name='idx_enterprise_active'),
        ]

    def __str__(self):
        return self.name


class EnterpriseAwareModel(models.Model):
    """
    Abstract base model for all enterprise-scoped models.
    Provides enterprise foreign key and common fields.
    """

    enterprise = models.ForeignKey(
        Enterprise,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Entreprise'
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """
    Abstract base model with created_at and updated_at fields.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Modifié le')

    class Meta:
        abstract = True


class AuditableModel(TimeStampedModel):
    """
    Abstract base model that tracks who created and modified the record.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_created',
        verbose_name='Créé par'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='%(class)s_updated',
        verbose_name='Modifié par'
    )

    class Meta:
        abstract = True
