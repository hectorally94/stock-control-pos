from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Location, LocationStock, LocationType

User = get_user_model()


# Roles allowed to act on stock (entries, transfers) — used to hide action buttons
STOCK_MANAGE_ROLES = ('admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager')


def role_required(*roles):
    """Decorator to check if the user has one of the required roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                return redirect('locations:dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
def dashboard(request):
    """Locations dashboard showing all locations for the enterprise"""
    user = request.user

    if user.role not in STOCK_MANAGE_ROLES + ('accountant',):
        messages.error(request, "Vous n'avez pas accès à cette page")
        return redirect('home')

    # Get locations for user's enterprise (incl. inactive, so nothing is hidden)
    if hasattr(user, 'enterprise') and user.enterprise:
        locations = Location.objects.filter(
            enterprise=user.enterprise
        ).select_related('manager', 'type_ref').order_by('-is_active', 'name')
    else:
        locations = Location.objects.none()

    # Separate warehouses and boutiques (by behaviour)
    warehouses = locations.filter(location_type='warehouse')
    boutiques = locations.filter(location_type='boutique')

    # Get stock stats per location
    location_stats = []
    for location in locations:
        stocks = LocationStock.objects.filter(location=location)
        total_items = stocks.count()
        # "Faible" = below threshold but still > 0; rupture has its own column
        low_stock_count = sum(1 for s in stocks if s.is_low_stock and s.quantity > 0)
        out_of_stock_count = stocks.filter(quantity__lte=0).count()

        location_stats.append({
            'location': location,
            'total_items': total_items,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
        })

    context = {
        'warehouses': warehouses,
        'boutiques': boutiques,
        'location_stats': location_stats,
        'total_locations': locations.count(),
        'can_create_location': user.role in ['admin', 'owner', 'manager'],
        'can_manage_types': user.role in ['admin', 'owner', 'manager'],
    }
    return render(request, 'locations/dashboard.html', context)


def _managers_for(enterprise):
    if not enterprise:
        return User.objects.none()
    return User.objects.filter(enterprise=enterprise, is_active=True).order_by('first_name', 'username')


def _active_types(enterprise):
    if not enterprise:
        return LocationType.objects.none()
    return LocationType.objects.filter(enterprise=enterprise, is_active=True).order_by('name')


def _location_data_from_post(post):
    """Normalize POST data into the dict the form template expects."""
    return {
        'name': post.get('name', '').strip(),
        'code': post.get('code', '').strip(),
        'type_id': post.get('type_id', '') or '',
        'address': post.get('address', '').strip(),
        'phone': post.get('phone', '').strip(),
        'email': post.get('email', '').strip(),
        'manager': post.get('manager', '') or '',
        'is_main_warehouse': post.get('is_main_warehouse') == 'on',
        'is_active': post.get('is_active') == 'on',
    }


def _location_data_from_instance(loc):
    return {
        'name': loc.name,
        'code': loc.code,
        'type_id': str(loc.type_ref_id or ''),
        'address': loc.address or '',
        'phone': loc.phone or '',
        'email': loc.email or '',
        'manager': str(loc.manager_id or ''),
        'is_main_warehouse': loc.is_main_warehouse,
        'is_active': loc.is_active,
    }


def _validate_location(data, enterprise, exclude_pk=None):
    """Validate the form; returns (errors, chosen_type_or_None)."""
    errors = []
    chosen_type = None
    if not enterprise:
        errors.append("Aucune entreprise n'est associée à votre compte.")
    if not data['name']:
        errors.append("Le nom est requis.")
    if not data['code']:
        errors.append("Le code est requis.")
    if not data['type_id']:
        errors.append("Le type d'emplacement est requis.")
    elif enterprise:
        chosen_type = LocationType.objects.filter(
            pk=data['type_id'], enterprise=enterprise, is_active=True
        ).first()
        if not chosen_type:
            errors.append("Le type d'emplacement sélectionné est invalide.")
    if data['code'] and enterprise:
        dup = Location.objects.filter(enterprise=enterprise, code=data['code'])
        if exclude_pk:
            dup = dup.exclude(pk=exclude_pk)
        if dup.exists():
            errors.append("Un emplacement avec ce code existe déjà.")
    return errors, chosen_type


@role_required('admin', 'owner', 'manager')
def location_create(request):
    """Create a new location."""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    if request.method == 'POST':
        data = _location_data_from_post(request.POST)
        errors, chosen_type = _validate_location(data, enterprise)
        manager = None
        if data['manager'] and enterprise:
            manager = User.objects.filter(pk=data['manager'], enterprise=enterprise).first()

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Location.objects.create(
                enterprise=enterprise,
                name=data['name'], code=data['code'],
                location_type=chosen_type.behaviour, type_ref=chosen_type,
                address=data['address'] or None, phone=data['phone'] or None, email=data['email'] or None,
                manager=manager, is_main_warehouse=data['is_main_warehouse'], is_active=data['is_active'],
                created_by=user,
            )
            messages.success(request, f"Emplacement « {data['name']} » créé avec succès.")
            return redirect('locations:dashboard')
    else:
        data = {'name': '', 'code': '', 'type_id': '', 'address': '', 'phone': '',
                'email': '', 'manager': '', 'is_main_warehouse': False, 'is_active': True}

    return render(request, 'locations/location_form.html', {
        'mode': 'create', 'data': data,
        'managers': _managers_for(enterprise),
        'types': _active_types(enterprise),
    })


@role_required('admin', 'owner', 'manager')
def location_edit(request, pk):
    """Edit an existing location."""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = get_object_or_404(Location, pk=pk)

    if enterprise and location.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cet emplacement.")
        return redirect('locations:dashboard')

    if request.method == 'POST':
        data = _location_data_from_post(request.POST)
        errors, chosen_type = _validate_location(data, enterprise, exclude_pk=location.pk)
        manager = None
        if data['manager'] and enterprise:
            manager = User.objects.filter(pk=data['manager'], enterprise=enterprise).first()

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            location.name = data['name']
            location.code = data['code']
            location.type_ref = chosen_type
            location.location_type = chosen_type.behaviour
            location.address = data['address'] or None
            location.phone = data['phone'] or None
            location.email = data['email'] or None
            location.manager = manager
            location.is_main_warehouse = data['is_main_warehouse']
            location.is_active = data['is_active']
            location.save()
            messages.success(request, f"Emplacement « {location.name} » mis à jour.")
            return redirect('locations:detail', pk=location.pk)
    else:
        data = _location_data_from_instance(location)

    return render(request, 'locations/location_form.html', {
        'mode': 'edit', 'data': data, 'location': location,
        'managers': _managers_for(enterprise),
        'types': _active_types(enterprise),
    })


@role_required('admin', 'owner', 'manager')
def location_delete(request, pk):
    """Delete a location (only if it holds no stock / movements / transfers)."""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)
    location = get_object_or_404(Location, pk=pk)

    if enterprise and location.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cet emplacement.")
        return redirect('locations:dashboard')

    if request.method != 'POST':
        return redirect('locations:detail', pk=location.pk)

    # Guard: block deletion when the location still has linked data.
    has_stock = LocationStock.objects.filter(location=location).exists() \
        or location.stocks.exists()
    has_movements = location.stock_movements.exists()
    has_transfers = location.outgoing_transfers.exists() or location.incoming_transfers.exists()

    if has_stock or has_movements or has_transfers:
        messages.error(
            request,
            "Impossible de supprimer cet emplacement : il contient du stock ou un historique. "
            "Désactivez-le plutôt (décochez « Actif » dans la modification)."
        )
        return redirect('locations:edit', pk=location.pk)

    name = location.name
    location.delete()
    messages.success(request, f"Emplacement « {name} » supprimé.")
    return redirect('locations:dashboard')


@login_required
def location_detail(request, pk):
    """Detail view for a specific location"""
    user = request.user

    location = get_object_or_404(Location, pk=pk)

    # Check user has access to this location's enterprise
    if hasattr(user, 'enterprise') and user.enterprise != location.enterprise:
        messages.error(request, "Vous n'avez pas accès à cet emplacement.")
        return redirect('locations:dashboard')

    # Cashiers may only consult their own boutique
    if user.role == 'cashier' and getattr(user, 'location', None) != location:
        messages.error(request, "Vous n'avez accès qu'à votre propre emplacement.")
        return redirect('home')

    # Get stock items for this location
    stocks = LocationStock.objects.filter(
        location=location
    ).select_related('product', 'product__category').order_by('product__name')

    # "Faible" = below threshold but still > 0; "Rupture" = 0 (don't double-count)
    low_stock_items = [s for s in stocks if s.is_low_stock and s.quantity > 0]
    out_of_stock_items = stocks.filter(quantity__lte=0)

    # Back button returns to wherever the user came from (e.g. a product page),
    # falling back to the locations dashboard. Validate to avoid open redirects.
    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        back_url = next_url
    else:
        back_url = reverse('locations:dashboard')

    context = {
        'location': location,
        'stocks': stocks,
        'low_stock_items': low_stock_items,
        'out_of_stock_count': out_of_stock_items.count(),
        'total_items': stocks.count(),
        'can_manage_location': user.role in ['admin', 'owner', 'manager'],
        'can_manage_stock': user.role in STOCK_MANAGE_ROLES,
        'back_url': back_url,
    }
    return render(request, 'locations/detail.html', context)


@login_required
def location_stock(request, pk):
    """Stock management for a specific location"""
    user = request.user

    location = get_object_or_404(Location, pk=pk)

    # Check user has access
    if hasattr(user, 'enterprise') and user.enterprise != location.enterprise:
        messages.error(request, "Vous n'avez pas accès à cet emplacement.")
        return redirect('locations:dashboard')

    # Cashiers may only consult their own boutique
    if user.role == 'cashier' and getattr(user, 'location', None) != location:
        messages.error(request, "Vous n'avez accès qu'à votre propre emplacement.")
        return redirect('home')

    # Get stock items
    stocks = LocationStock.objects.filter(
        location=location
    ).select_related('product', 'product__category').order_by('product__name')

    # Filter by category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        stocks = stocks.filter(product__category_id=category_filter)

    # Filter by stock status
    stock_status = request.GET.get('status')
    if stock_status == 'low':
        stocks = [s for s in stocks if s.is_low_stock and s.quantity > 0]
    elif stock_status == 'out':
        stocks = stocks.filter(quantity__lte=0)
    elif stock_status == 'alert':
        # Faible + Rupture combined — matches the "Alertes" tiles on dashboards
        stocks = [s for s in stocks if s.is_low_stock]

    # Export (respects the active filters)
    from apps.core.exports import export_list_response, fmt_qty
    export = export_list_response(
        request,
        title=f"Stock — {location.name}",
        headers=["Produit", "Catégorie", "Quantité", "Seuil min", "Unité", "Statut"],
        rows=(
            [
                s.product.name,
                s.product.category.name if s.product.category else '',
                fmt_qty(s.quantity),
                fmt_qty(s.min_stock_threshold),
                s.product.unit,
                'Rupture' if s.quantity <= 0 else ('Stock faible' if s.is_low_stock else 'OK'),
            ]
            for s in stocks
        ),
        filename=f"stock_{location.code or location.pk}",
    )
    if export:
        return export

    # Get categories for filter
    from apps.products.models import Category
    categories = Category.objects.filter(enterprise=user.enterprise) if hasattr(user, 'enterprise') else Category.objects.none()

    context = {
        'location': location,
        'stocks': stocks,
        'categories': categories,
        'selected_category': category_filter,
        'selected_status': stock_status,
        'can_manage_stock': user.role in STOCK_MANAGE_ROLES,
    }
    return render(request, 'locations/stock.html', context)


# =============================================================================
# LOCATION TYPE MANAGEMENT (manageable Emplacement types)
# =============================================================================

@role_required('admin', 'owner', 'manager')
def type_list(request):
    """List the enterprise's location types with usage counts."""
    enterprise = getattr(request.user, 'enterprise', None)
    types = (
        LocationType.objects.filter(enterprise=enterprise).order_by('name')
        if enterprise else LocationType.objects.none()
    )
    types = types.annotate(usage=Count('locations'))
    return render(request, 'locations/type_list.html', {
        'types': types,
        'behaviour_choices': LocationType.BEHAVIOUR_CHOICES,
    })


def _type_data_from_post(post):
    return {
        'name': post.get('name', '').strip(),
        'behaviour': post.get('behaviour', ''),
        'is_active': post.get('is_active') == 'on',
    }


def _validate_type(data, enterprise, exclude_pk=None):
    errors = []
    if not enterprise:
        errors.append("Aucune entreprise n'est associée à votre compte.")
    if not data['name']:
        errors.append("Le nom du type est requis.")
    if data['behaviour'] not in dict(LocationType.BEHAVIOUR_CHOICES):
        errors.append("Le comportement est invalide.")
    if data['name'] and enterprise:
        dup = LocationType.objects.filter(enterprise=enterprise, name=data['name'])
        if exclude_pk:
            dup = dup.exclude(pk=exclude_pk)
        if dup.exists():
            errors.append("Un type avec ce nom existe déjà.")
    return errors


@role_required('admin', 'owner', 'manager')
def type_create(request):
    """Create a new location type."""
    enterprise = getattr(request.user, 'enterprise', None)

    if request.method == 'POST':
        data = _type_data_from_post(request.POST)
        errors = _validate_type(data, enterprise)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            LocationType.objects.create(
                enterprise=enterprise,
                name=data['name'], behaviour=data['behaviour'], is_active=data['is_active'],
            )
            messages.success(request, f"Type « {data['name']} » créé avec succès.")
            return redirect('locations:type_list')
    else:
        data = {'name': '', 'behaviour': 'boutique', 'is_active': True}

    return render(request, 'locations/type_form.html', {
        'mode': 'create', 'data': data,
        'behaviour_choices': LocationType.BEHAVIOUR_CHOICES,
    })


@role_required('admin', 'owner', 'manager')
def type_edit(request, pk):
    """Edit a location type."""
    enterprise = getattr(request.user, 'enterprise', None)
    loc_type = get_object_or_404(LocationType, pk=pk)

    if enterprise and loc_type.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce type.")
        return redirect('locations:type_list')

    if request.method == 'POST':
        data = _type_data_from_post(request.POST)
        errors = _validate_type(data, enterprise, exclude_pk=loc_type.pk)
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            loc_type.name = data['name']
            loc_type.behaviour = data['behaviour']
            loc_type.is_active = data['is_active']
            loc_type.save()
            # Keep dependent locations' behaviour in sync with their type.
            loc_type.locations.update(location_type=loc_type.behaviour)
            messages.success(request, f"Type « {loc_type.name} » mis à jour.")
            return redirect('locations:type_list')
    else:
        data = {'name': loc_type.name, 'behaviour': loc_type.behaviour, 'is_active': loc_type.is_active}

    return render(request, 'locations/type_form.html', {
        'mode': 'edit', 'data': data, 'loc_type': loc_type,
        'behaviour_choices': LocationType.BEHAVIOUR_CHOICES,
    })


@role_required('admin', 'owner', 'manager')
def type_delete(request, pk):
    """Delete a location type (blocked if any location uses it)."""
    enterprise = getattr(request.user, 'enterprise', None)
    loc_type = get_object_or_404(LocationType, pk=pk)

    if enterprise and loc_type.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce type.")
        return redirect('locations:type_list')

    if request.method != 'POST':
        return redirect('locations:type_list')

    if loc_type.locations.exists():
        messages.error(
            request,
            "Impossible de supprimer ce type : des emplacements l'utilisent. "
            "Désactivez-le plutôt, ou réaffectez ces emplacements à un autre type."
        )
        return redirect('locations:type_list')

    name = loc_type.name
    loc_type.delete()
    messages.success(request, f"Type « {name} » supprimé.")
    return redirect('locations:type_list')
