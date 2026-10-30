from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from apps.customers.models import Customer, CustomerCredit, CreditPayment
from api.v1.serializers import (
    CustomerSerializer, CustomerListSerializer,
    CustomerCreditSerializer, CreditPaymentSerializer
)
from api.v1.permissions import IsAdminOrManager, IsCashier


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Customer management.
    Cashiers can view and create customers, admin/manager can update/delete.
    """
    
    queryset = Customer.objects.prefetch_related('credits').all()
    serializer_class = CustomerSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'phone', 'email']
    ordering_fields = ['name', 'total_purchases', 'current_balance', 'created_at']
    ordering = ['name']
    
    # Rôle : utilise CustomerListSerializer pour la liste et CustomerSerializer pour les autres actions.
    # Liens : appelée par DRF ; serializers dans api/v1/serializers/customers.py.
    def get_serializer_class(self):
        """Use minimal serializer for list view"""
        if self.action == 'list':
            return CustomerListSerializer
        return CustomerSerializer
    
    # Rôle : réserve modification et suppression à IsAdminOrManager ; le reste, création comprise, à IsCashier.
    # Liens : appelée par DRF ; classes définies dans api/v1/permissions.py.
    def get_permissions(self):
        """Cashiers can view/create, admin/manager can update/delete"""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminOrManager()]
        return [IsCashier()]
    
    # Rôle : renvoie les 10 clients actifs ayant le plus grand total_purchases.
    # Liens : route GET /api/v1/customers/top_customers/ ; total alimenté par apps/customers/signals.py.
    @action(detail=False, methods=['get'])
    def top_customers(self, request):
        """
        Get top 10 customers by total purchases.
        """
        customers = self.get_queryset().filter(is_active=True).order_by('-total_purchases')[:10]
        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)
    
    # Rôle : renvoie les clients actifs dont current_balance est supérieur à 0.
    # Liens : route GET /api/v1/customers/with_credits/ ; solde modifié par apps/customers/signals.py.
    @action(detail=False, methods=['get'])
    def with_credits(self, request):
        """
        Get customers with outstanding credit (current_balance > 0).
        """
        customers = self.get_queryset().filter(current_balance__gt=0, is_active=True)
        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)


class CustomerCreditViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CustomerCredit management.
    """
    
    queryset = CustomerCredit.objects.select_related('customer', 'sale').prefetch_related('payments').all()
    serializer_class = CustomerCreditSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'status']
    search_fields = ['customer__name', 'sale__sale_number']
    ordering_fields = ['created_at', 'due_date', 'remaining_amount']
    ordering = ['-created_at']
    
    # Rôle : filtre en Python les crédits en retard selon la propriété is_overdue, sans pagination.
    # Liens : route GET /api/v1/customer-credits/overdue/ ; is_overdue est dans apps/customers/models.py.
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """
        Get overdue credits.
        """
        credits = [credit for credit in self.get_queryset() if credit.is_overdue]
        serializer = self.get_serializer(credits, many=True)
        return Response(serializer.data)


class CreditPaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CreditPayment management.
    """
    
    queryset = CreditPayment.objects.select_related('credit', 'credit__customer', 'user').all()
    serializer_class = CreditPaymentSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['credit', 'payment_method', 'user']
    search_fields = ['credit__customer__name', 'payment_reference']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    # Rôle : enregistre le paiement de crédit au nom de l'utilisateur connecté.
    # Liens : POST /api/v1/credit-payments/ ; CreditPayment.save() (apps/customers/models.py) réduit le crédit.
    def perform_create(self, serializer):
        """Set current user when creating payment"""
        serializer.save(user=self.request.user)

