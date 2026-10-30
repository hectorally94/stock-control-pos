from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.exceptions import ValidationError
from django.db import models

from apps.transfers.models import Transfer, TransferItem
from apps.core.permissions import CanManageTransfers, CanReceiveTransfers
from apps.core.mixins import EnterpriseViewSetMixin
from api.v1.serializers.transfers import (
    TransferSerializer, TransferListSerializer, TransferCreateSerializer,
    TransferItemSerializer, TransferSendSerializer, TransferReceiveSerializer,
    TransferCancelSerializer
)


class TransferViewSet(EnterpriseViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Transfer management.
    Handles inter-location stock transfers.
    """

    queryset = Transfer.objects.select_related(
        'enterprise', 'source_location', 'destination_location',
        'created_by', 'sent_by', 'received_by', 'cancelled_by'
    ).prefetch_related('items__product')
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated, CanManageTransfers]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'source_location', 'destination_location']
    search_fields = ['reference', 'notes']
    ordering_fields = ['created_at', 'sent_at', 'received_at', 'reference']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return TransferListSerializer
        if self.action == 'create':
            return TransferCreateSerializer
        if self.action == 'send':
            return TransferSendSerializer
        if self.action == 'receive':
            return TransferReceiveSerializer
        if self.action == 'cancel':
            return TransferCancelSerializer
        return TransferSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by enterprise
        if hasattr(user, 'enterprise') and user.enterprise:
            queryset = queryset.filter(enterprise=user.enterprise)

        # Filter by location for non-owners
        if hasattr(user, 'location') and user.location and user.role not in ['owner', 'admin', 'manager']:
            queryset = queryset.filter(
                models.Q(source_location=user.location) |
                models.Q(destination_location=user.location)
            )

        return queryset

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending transfers (drafts and awaiting approval)"""
        queryset = self.get_queryset().filter(status__in=['draft', 'pending'])
        serializer = TransferListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def in_transit(self, request):
        """Get transfers that are in transit"""
        queryset = self.get_queryset().filter(status='in_transit')
        serializer = TransferListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def incoming(self, request):
        """Get incoming transfers for user's location"""
        user = request.user
        if hasattr(user, 'location') and user.location:
            queryset = self.get_queryset().filter(
                destination_location=user.location,
                status='in_transit'
            )
        else:
            queryset = self.get_queryset().filter(status='in_transit')
        serializer = TransferListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def outgoing(self, request):
        """Get outgoing transfers from user's location"""
        user = request.user
        if hasattr(user, 'location') and user.location:
            queryset = self.get_queryset().filter(
                source_location=user.location,
                status__in=['draft', 'pending', 'in_transit']
            )
        else:
            queryset = self.get_queryset().filter(status__in=['draft', 'pending', 'in_transit'])
        serializer = TransferListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Send a transfer (mark as in_transit)"""
        transfer = self.get_object()
        try:
            transfer.send(request.user)
            serializer = TransferSerializer(transfer)
            return Response(serializer.data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, CanReceiveTransfers])
    def receive(self, request, pk=None):
        """Receive a transfer"""
        transfer = self.get_object()
        serializer = TransferReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update received quantities if provided
        items_data = serializer.validated_data.get('items', [])
        for item_data in items_data:
            try:
                item = TransferItem.objects.get(
                    id=item_data['id'],
                    transfer=transfer
                )
                if 'received_quantity' in item_data:
                    item.received_quantity = item_data['received_quantity']
                    item.save()
            except TransferItem.DoesNotExist:
                pass

        try:
            transfer.receive(request.user)
            return Response(TransferSerializer(transfer).data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a transfer"""
        transfer = self.get_object()
        serializer = TransferCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transfer.cancel(request.user, serializer.validated_data['reason'])
            return Response(TransferSerializer(transfer).data)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class TransferItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TransferItem management.
    Items are managed through the Transfer ViewSet primarily.
    """

    queryset = TransferItem.objects.select_related('transfer', 'product')
    serializer_class = TransferItemSerializer
    permission_classes = [IsAuthenticated, CanManageTransfers]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['transfer']
    search_fields = ['product__name']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by enterprise through transfer
        if hasattr(user, 'enterprise') and user.enterprise:
            queryset = queryset.filter(transfer__enterprise=user.enterprise)

        return queryset
