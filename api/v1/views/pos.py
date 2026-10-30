from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from apps.pos.models import Sale, SaleItem
from api.v1.serializers import (
    SaleSerializer, SaleListSerializer, SaleItemSerializer, SaleCreateSerializer
)
from api.v1.permissions import IsCashier, IsAdminOrManager


class SaleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Sale management.
    Cashiers can create sales, admin/manager can view all and manage.
    """
    
    queryset = Sale.objects.select_related('customer', 'user').prefetch_related('items__product').all()
    serializer_class = SaleSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'user', 'payment_method', 'status']
    search_fields = ['sale_number', 'customer__name', 'user__username']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    
    # Rôle : choisit SaleListSerializer pour la liste, SaleCreateSerializer pour la création, sinon SaleSerializer.
    # Liens : appelée par DRF ; serializers dans api/v1/serializers/pos.py.
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'list':
            return SaleListSerializer
        elif self.action == 'create':
            return SaleCreateSerializer
        return SaleSerializer
    
    # Rôle : ajoute seulement le caissier connecté ; enterprise et location de la vente restent vides.
    # Liens : POST /api/v1/sales/ ; lance SaleCreateSerializer.create(), puis les signaux de apps/pos/signals.py.
    def perform_create(self, serializer):
        """Set current user as cashier when creating sale"""
        serializer.save(user=self.request.user)
    
    # Rôle : additionne les ventes completed du jour et détaille le total par mode de paiement (None devient 0).
    # Liens : route GET /api/v1/sales/today_summary/ ; agrège Sale (apps/pos/models.py) ; voir tests/test_api.py.
    @action(detail=False, methods=['get'])
    def today_summary(self, request):
        """
        Get today's sales summary.
        Returns: count, total amount, breakdown by payment method.
        """
        today = timezone.now().date()
        sales = self.get_queryset().filter(created_at__date=today, status='completed')
        
        summary = sales.aggregate(
            count=Count('id'),
            total=Sum('total_amount'),
            cash=Sum('total_amount', filter=Q(payment_method='cash')),
            mobile_money=Sum('total_amount', filter=Q(payment_method='mobile_money')),
            card=Sum('total_amount', filter=Q(payment_method='card')),
            credit=Sum('total_amount', filter=Q(payment_method='credit')),
        )
        
        # Convert None to 0
        for key in summary:
            if summary[key] is None:
                summary[key] = 0

        # Expose an explicit `total_sales` alias alongside the raw `total`.
        summary['total_sales'] = summary['total']

        return Response(summary)
    
    # Rôle : renvoie la vente en JSON ; la branche PDF exige ?format=pdf|thermal, que DRF rejette d'abord en 404.
    # Liens : GET /api/v1/sales/<id>/receipt/ ; branche PDF : apps/pos/utils/receipt_generator.py et un ActionLog.
    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """
        Get receipt data or generate PDF.
        Query param: format (json, pdf, thermal)
        """
        sale = self.get_object()
        format_type = request.query_params.get('format', 'json')
        
        if format_type in ['pdf', 'thermal']:
            # Generate PDF receipt
            from apps.pos.utils.receipt_generator import generate_receipt_pdf
            from django.http import HttpResponse
            
            pdf_buffer = generate_receipt_pdf(sale, format=format_type)
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Recu_{sale.sale_number}.pdf"'
            
            # Log receipt generation
            from apps.accounts.models import ActionLog
            ActionLog.objects.create(
                user=request.user,
                action_type='create',
                entity_type='receipt',
                entity_id=sale.id,
                description=f'Reçu PDF généré pour vente {sale.sale_number}'
            )
            
            return response
        else:
            # Return JSON data
            serializer = self.get_serializer(sale)
            return Response(serializer.data)
    
    # Rôle : passe la vente à cancelled, sauf si déjà annulée ; le stock revient seulement si elle était completed.
    # Liens : route POST /api/v1/sales/<id>/cancel/ ; apps/pos/signals.py crée les entrées de stock et journalise.
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def cancel(self, request, pk=None):
        """
        Cancel a sale (admin/manager only).
        """
        sale = self.get_object()
        
        if sale.status == 'cancelled':
            return Response(
                {'error': 'Cette vente est déjà annulée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sale.status = 'cancelled'
        sale.save()
        
        return Response({'message': 'Vente annulée avec succès'})
    
    # Rôle : passe la vente à refunded, sauf si déjà fait ; le stock revient seulement si elle était completed.
    # Liens : route POST /api/v1/sales/<id>/refund/ ; apps/pos/signals.py crée les entrées et journalise.
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrManager])
    def refund(self, request, pk=None):
        """
        Refund a sale (admin/manager only).
        """
        sale = self.get_object()
        
        if sale.status == 'refunded':
            return Response(
                {'error': 'Cette vente est déjà remboursée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sale.status = 'refunded'
        sale.save()
        
        return Response({'message': 'Vente remboursée avec succès'})


class SaleItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for SaleItem (read-only).
    """
    
    queryset = SaleItem.objects.select_related('sale', 'product').all()
    serializer_class = SaleItemSerializer
    permission_classes = [IsCashier]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['sale', 'product']
    ordering_fields = ['sale__created_at']
    ordering = ['-sale__created_at']

