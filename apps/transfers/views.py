from decimal import Decimal, InvalidOperation

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Transfer, TransferItem
from apps.locations.models import Location, LocationStock
from apps.products.models import Product


# Roles allowed to act on transfers (create/send/receive/cancel) — moving stock
TRANSFER_MANAGE_ROLES = ('admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager')
# Roles allowed to view transfers (accountant = read-only)
TRANSFER_VIEW_ROLES = TRANSFER_MANAGE_ROLES + ('accountant',)


def _fmt_qty(value):
    """Format a quantity without trailing zeros: 5.000 -> '5', 2.500 -> '2.5'."""
    s = f"{value:.3f}".rstrip('0').rstrip('.')
    return s or '0'


@login_required
def transfer_list(request):
    """List all transfers for the enterprise"""
    user = request.user

    if user.role not in TRANSFER_VIEW_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    # Get transfers for user's enterprise
    if hasattr(user, 'enterprise') and user.enterprise:
        transfers = Transfer.objects.filter(
            enterprise=user.enterprise
        ).select_related(
            'source_location', 'destination_location', 'created_by'
        ).order_by('-created_at')
    else:
        transfers = Transfer.objects.none()

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        transfers = transfers.filter(status=status_filter)

    # Filter by location (source or destination)
    location_filter = request.GET.get('location')
    if location_filter:
        transfers = transfers.filter(
            Q(source_location_id=location_filter) |
            Q(destination_location_id=location_filter)
        )

    # Filter by direction relative to a location
    source_filter = request.GET.get('source')
    if source_filter:
        transfers = transfers.filter(source_location_id=source_filter)

    destination_filter = request.GET.get('destination')
    if destination_filter:
        transfers = transfers.filter(destination_location_id=destination_filter)

    # Export (respects the active filters)
    from apps.core.exports import export_list_response
    export = export_list_response(
        request,
        title="Transferts de Stock",
        headers=["Référence", "Statut", "Source", "Destination", "Articles", "Créé par", "Date"],
        rows=(
            [
                t.reference,
                t.get_status_display(),
                t.source_location.name,
                t.destination_location.name,
                t.items.count(),
                t.created_by.get_full_name() or t.created_by.username if t.created_by else '',
                t.created_at,
            ]
            for t in transfers
        ),
        filename="transferts",
    )
    if export:
        return export

    # Get locations for filter dropdown
    locations = Location.objects.filter(
        enterprise=user.enterprise, is_active=True
    ) if hasattr(user, 'enterprise') and user.enterprise else Location.objects.none()

    # Stats
    pending_count = transfers.filter(status='pending').count()
    in_transit_count = transfers.filter(status='in_transit').count()

    context = {
        'transfers': transfers[:50],  # Limit to 50 for performance
        'locations': locations,
        'selected_status': status_filter,
        'selected_location': location_filter,
        'pending_count': pending_count,
        'in_transit_count': in_transit_count,
        'status_choices': Transfer.STATUS_CHOICES,
        'can_manage_transfers': user.role in TRANSFER_MANAGE_ROLES,
    }
    return render(request, 'transfers/list.html', context)


@login_required
def transfer_detail(request, pk):
    """Detail view for a specific transfer"""
    user = request.user

    if user.role not in TRANSFER_VIEW_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    transfer = get_object_or_404(Transfer, pk=pk)

    # Check user has access to this transfer's enterprise
    if hasattr(user, 'enterprise') and user.enterprise != transfer.enterprise:
        messages.error(request, "Vous n'avez pas accès à ce transfert.")
        return redirect('transfers:list')

    # Get transfer items
    items = transfer.items.select_related('product').all()

    context = {
        'transfer': transfer,
        'items': items,
        'can_manage_transfers': user.role in TRANSFER_MANAGE_ROLES,
    }
    return render(request, 'transfers/detail.html', context)


@login_required
def transfer_create(request):
    """Create a new transfer"""
    user = request.user

    if user.role not in TRANSFER_MANAGE_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    if not hasattr(user, 'enterprise') or not user.enterprise:
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('transfers:list')

    # Get locations for the enterprise
    locations = Location.objects.filter(
        enterprise=user.enterprise, is_active=True
    ).order_by('location_type', 'name')

    # Pre-select source location from URL parameter
    source_id = request.GET.get('source')
    preselected_source = None
    if source_id:
        try:
            preselected_source = locations.get(pk=source_id)
        except Location.DoesNotExist:
            pass

    # Pre-select product from URL parameter
    product_id = request.GET.get('product')
    preselected_product = None
    if product_id:
        try:
            preselected_product = Product.objects.get(pk=product_id, enterprise=user.enterprise)
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        source_location_id = request.POST.get('source_location')
        destination_location_id = request.POST.get('destination_location')
        notes = request.POST.get('notes', '')

        # Validate locations
        try:
            source_location = Location.objects.get(pk=source_location_id, enterprise=user.enterprise)
            destination_location = Location.objects.get(pk=destination_location_id, enterprise=user.enterprise)
        except Location.DoesNotExist:
            messages.error(request, "Emplacement invalide.")
            return redirect('transfers:create')

        if source_location == destination_location:
            messages.error(request, "La source et la destination doivent être différentes.")
            return redirect('transfers:create')

        # Validate items against available stock at the source BEFORE creating anything
        product_ids = request.POST.getlist('product_id')
        quantities = request.POST.getlist('quantity')

        valid_items = []
        stock_errors = []
        for pid, qty in zip(product_ids, quantities):
            if not (pid and qty):
                continue
            try:
                product = Product.objects.get(pk=pid, enterprise=user.enterprise)
                quantity = Decimal(qty)
            except (Product.DoesNotExist, InvalidOperation):
                continue
            if quantity <= 0:
                continue

            stock = LocationStock.objects.filter(
                location=source_location, product=product
            ).first()
            available = stock.quantity if stock else Decimal('0')
            if quantity > available:
                stock_errors.append(
                    f"{product.name} : demandé {_fmt_qty(quantity)}, disponible {_fmt_qty(available)}"
                )
                continue
            valid_items.append((product, quantity))

        if stock_errors:
            messages.error(
                request,
                "Stock insuffisant à la source — " + " ; ".join(stock_errors)
            )
            return redirect('transfers:create')

        if not valid_items:
            messages.error(request, "Aucun article valide dans le transfert.")
            return redirect('transfers:create')

        # Create transfer
        transfer = Transfer.objects.create(
            enterprise=user.enterprise,
            source_location=source_location,
            destination_location=destination_location,
            notes=notes,
            created_by=user,
            status='draft'
        )

        for product, quantity in valid_items:
            TransferItem.objects.create(
                transfer=transfer,
                product=product,
                quantity=quantity
            )

        messages.success(request, f"Transfert {transfer.reference} créé avec succès.")
        return redirect('transfers:detail', pk=transfer.pk)

    # Get products with stock at potential source locations
    products = Product.objects.filter(
        enterprise=user.enterprise, is_active=True
    ).select_related('category').order_by('name')

    # Per-location stock map so the form can show availability at the chosen
    # source and cap the quantity input: {product_id: {location_id: qty}}
    stock_map = {}
    for ls in LocationStock.objects.filter(location__in=locations):
        stock_map.setdefault(ls.product_id, {})[str(ls.location_id)] = float(ls.quantity)

    products_json = [
        {
            'id': p.id,
            'label': f"{p.name} ({p.category.name})" if p.category else p.name,
            'unit': p.unit,
            'stock': stock_map.get(p.id, {}),
        }
        for p in products
    ]

    context = {
        'locations': locations,
        'products': products,
        'products_json': products_json,
        'preselected_source': preselected_source,
        'preselected_product': preselected_product,
    }
    return render(request, 'transfers/create.html', context)


@login_required
def transfer_send(request, pk):
    """Send a transfer (mark as in transit)"""
    user = request.user

    if user.role not in TRANSFER_MANAGE_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette action")
        return redirect('home')

    transfer = get_object_or_404(Transfer, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != transfer.enterprise:
        messages.error(request, "Vous n'avez pas accès à ce transfert.")
        return redirect('transfers:list')

    if request.method == 'POST':
        try:
            transfer.send(user)
            messages.success(request, f"Transfert {transfer.reference} envoyé avec succès.")
        except ValidationError as e:
            messages.error(request, str(e))

    return redirect('transfers:detail', pk=pk)


@login_required
def transfer_receive(request, pk):
    """Receive a transfer"""
    user = request.user

    if user.role not in TRANSFER_MANAGE_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette action")
        return redirect('home')

    transfer = get_object_or_404(Transfer, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != transfer.enterprise:
        messages.error(request, "Vous n'avez pas accès à ce transfert.")
        return redirect('transfers:list')

    if request.method == 'POST':
        try:
            # Update received quantities if provided
            for item in transfer.items.all():
                received_qty = request.POST.get(f'received_qty_{item.pk}')
                if received_qty:
                    try:
                        item.received_quantity = float(received_qty)
                        item.save()
                    except ValueError:
                        pass

            transfer.receive(user)
            messages.success(request, f"Transfert {transfer.reference} reçu avec succès.")
        except ValidationError as e:
            messages.error(request, str(e))

    return redirect('transfers:detail', pk=pk)


@login_required
def transfer_cancel(request, pk):
    """Cancel a transfer"""
    user = request.user

    if user.role not in TRANSFER_MANAGE_ROLES:
        messages.error(request, "Vous n'avez pas accès à cette action")
        return redirect('home')

    transfer = get_object_or_404(Transfer, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != transfer.enterprise:
        messages.error(request, "Vous n'avez pas accès à ce transfert.")
        return redirect('transfers:list')

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Annulé par utilisateur')
        try:
            transfer.cancel(user, reason)
            messages.success(request, f"Transfert {transfer.reference} annulé.")
        except ValidationError as e:
            messages.error(request, str(e))

    return redirect('transfers:detail', pk=pk)
