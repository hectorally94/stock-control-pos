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
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'list':
            return SaleListSerializer
        elif self.action == 'create':
            return SaleCreateSerializer
        return SaleSerializer
    
    def perform_create(self, serializer):
        """Set current user as cashier when creating sale"""
        serializer.save(user=self.request.user)
    
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

