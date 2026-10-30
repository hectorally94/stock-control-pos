from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count
from django.utils import timezone

from apps.accounting.models import ExpenseCategory, Expense, CashRegisterSession, DailySummary
from api.v1.serializers import (
    ExpenseCategorySerializer, ExpenseSerializer,
    CashRegisterSessionSerializer, DailySummarySerializer
)
from api.v1.permissions import IsAdminOrManager, IsAccountant


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ExpenseCategory management.
    """
    
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAccountant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ExpenseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Expense management.
    """
    
    queryset = Expense.objects.select_related('expense_category', 'user').all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAccountant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['expense_category', 'payment_method', 'is_recurring', 'user']
    search_fields = ['description', 'supplier', 'reference']
    ordering_fields = ['expense_date', 'amount', 'created_at']
    ordering = ['-expense_date']
    
    # Rôle : enregistre la dépense au nom de l'utilisateur connecté ; user est en lecture seule côté client.
    # Liens : appelée par DRF sur POST /api/v1/expenses/ ; crée Expense (apps/accounting/models.py).
    def perform_create(self, serializer):
        """Set current user when creating expense"""
        serializer.save(user=self.request.user)
    
    # Rôle : renvoie le total et le nombre de dépenses, filtrés par start_date, end_date et category_id.
    # Liens : route GET /api/v1/expenses/summary/ ; agrège Expense (apps/accounting/models.py).
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get expense summary with filters.
        Query params: start_date, end_date, category_id
        """
        queryset = self.get_queryset()
        
        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(expense_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(expense_date__lte=end_date)
        
        # Filter by category
        category_id = request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(expense_category_id=category_id)
        
        summary = queryset.aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        return Response(summary)


class CashRegisterSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CashRegisterSession management.
    """
    
    queryset = CashRegisterSession.objects.select_related('user').all()
    serializer_class = CashRegisterSessionSerializer
    permission_classes = [IsAdminOrManager]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'status']
    search_fields = ['user__username']
    ordering_fields = ['opened_at', 'closed_at']
    ordering = ['-opened_at']
    
    # Rôle : renvoie la première session ouverte de l'utilisateur connecté, sinon une réponse 404.
    # Liens : route GET /api/v1/cash-register-sessions/current_session/ ; lit CashRegisterSession.
    @action(detail=False, methods=['get'])
    def current_session(self, request):
        """
        Get current open session for the logged-in user.
        """
        session = self.get_queryset().filter(user=request.user, status='open').first()
        if session:
            serializer = self.get_serializer(session)
            return Response(serializer.data)
        return Response({'message': 'Aucune session ouverte'}, status=status.HTTP_404_NOT_FOUND)
    
    # Rôle : ferme la session ; sans expected_balance, ce solde prend closing_balance et la différence vaut 0.
    # Liens : route POST /api/v1/cash-register-sessions/<id>/close_session/ ; enregistre CashRegisterSession.
    @action(detail=True, methods=['post'])
    def close_session(self, request, pk=None):
        """
        Close a cash register session.
        """
        session = self.get_object()
        
        if session.status == 'closed':
            return Response(
                {'error': 'Cette session est déjà fermée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        closing_balance = request.data.get('closing_balance')
        expected_balance = request.data.get('expected_balance')
        
        if closing_balance is None:
            return Response(
                {'error': 'Le solde de fermeture est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.closing_balance = closing_balance
        session.expected_balance = expected_balance or closing_balance
        session.difference = float(closing_balance) - float(session.expected_balance)
        session.closed_at = timezone.now()
        session.status = 'closed'
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)


class DailySummaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DailySummary (mostly read-only, generated by command).
    """
    
    queryset = DailySummary.objects.all()
    serializer_class = DailySummarySerializer
    permission_classes = [IsAccountant]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['summary_date']
    ordering_fields = ['summary_date']
    ordering = ['-summary_date']
    
    # Rôle : renvoie le résumé d'une date (aujourd'hui par défaut) sans le créer ; 404 s'il n'existe pas.
    # Liens : route GET /api/v1/daily-summaries/daily_summary/ ; données créées par generate_daily_summary.
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """
        Get or create daily summary for a specific date.
        Query param: date (YYYY-MM-DD), defaults to today.
        """
        date_str = request.query_params.get('date')
        if date_str:
            try:
                from datetime import datetime
                summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            summary_date = timezone.now().date()
        
        summary = self.get_queryset().filter(summary_date=summary_date).first()
        
        if summary:
            serializer = self.get_serializer(summary)
            return Response(serializer.data)
        
        return Response(
            {'message': 'Aucun résumé trouvé pour cette date. Exécutez la commande generate_daily_summary.'},
            status=status.HTTP_404_NOT_FOUND
        )

