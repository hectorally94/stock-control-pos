"""
Frontend views for Product and Category management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q, Count, Sum, Prefetch
from django.core.paginator import Paginator

from .models import Category, Product
from apps.stock.models import Stock
from apps.locations.models import Location, LocationStock


# Rôle : fabrique un décorateur de vue qui limite l'accès aux rôles donnés.
# Liens : appliqué aux vues d'ici ; même logique dans apps/accounting/views.py et apps/customers/views.py.
def role_required(*roles):
    """Decorator to check if user has required role"""
    # Rôle : reçoit la vue à protéger et renvoie wrapper ; contrairement aux autres copies, sans @wraps.
    # Liens : utilisé uniquement par role_required, dans ce fichier.
    def decorator(view_func):
        # Rôle : renvoie l'anonyme vers login et le mauvais rôle vers home avec un message, sinon exécute la vue.
        # Liens : routes login et home de stock_control/urls.py ; lit User.role (apps/accounts/models.py).
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                return redirect('home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# CATEGORY VIEWS
# =============================================================================

# Rôle : liste les catégories de l'entreprise et les globales, avec le nombre de produits actifs et des filtres.
# Liens : route /products/categories/, lien depuis product_list.html ; rend category_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager')
def category_list(request):
    """List all categories"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    # Get categories with product count
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('name')

    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        categories = categories.filter(is_active=True)
    elif status_filter == 'inactive':
        categories = categories.filter(is_active=False)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        categories = categories.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    # Stats
    total_categories = categories.count()
    active_categories = categories.filter(is_active=True).count()

    context = {
        'categories': categories,
        'selected_status': status_filter,
        'search': search,
        'total_categories': total_categories,
        'active_categories': active_categories,
    }
    return render(request, 'products/category_list.html', context)


# Rôle : crée une catégorie après contrôle du nom (requis, unique dans l'entreprise, casse ignorée).
# Liens : route /products/categories/create/, liens dans category_list.html et product_form.html.
@login_required
@role_required('admin', 'owner', 'manager')
def category_create(request):
    """Create a new category"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        # Validate
        errors = []

        if not name:
            errors.append("Le nom de la catégorie est requis.")
        elif Category.objects.filter(name__iexact=name, enterprise=enterprise).exists():
            errors.append("Une catégorie avec ce nom existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            category = Category.objects.create(
                name=name,
                description=description,
                is_active=is_active,
                enterprise=enterprise,
            )
            messages.success(request, f"Catégorie '{category.name}' créée avec succès.")
            return redirect('products:category_list')

    return render(request, 'products/category_form.html', {'mode': 'create'})


# Rôle : modifie une catégorie accessible à l'entreprise de l'utilisateur, avec les mêmes contrôles de nom.
# Liens : route /products/categories/<pk>/edit/, lien depuis category_list.html ; rend category_form.html.
@login_required
@role_required('admin', 'owner', 'manager')
def category_edit(request, pk):
    """Edit a category"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    category = get_object_or_404(Category, pk=pk)

    # Check access
    if enterprise and category.enterprise and category.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette catégorie.")
        return redirect('products:category_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        # Validate
        errors = []

        if not name:
            errors.append("Le nom de la catégorie est requis.")
        elif Category.objects.filter(name__iexact=name, enterprise=enterprise).exclude(pk=pk).exists():
            errors.append("Une catégorie avec ce nom existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            category.name = name
            category.description = description
            category.is_active = is_active
            category.save()

            messages.success(request, f"Catégorie '{category.name}' modifiée avec succès.")
            return redirect('products:category_list')

    context = {
        'mode': 'edit',
        'category': category,
    }
    return render(request, 'products/category_form.html', context)


# Rôle : supprime définitivement la catégorie sur POST, sauf si des produits, même inactifs, l'utilisent.
# Liens : route /products/categories/<pk>/delete/, formulaire de category_list.html ; supprime la Category.
@login_required
@role_required('admin', 'owner', 'manager')
def category_delete(request, pk):
    """Delete a category"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    category = get_object_or_404(Category, pk=pk)

    # Check access
    if enterprise and category.enterprise and category.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette catégorie.")
        return redirect('products:category_list')

    # Check if category has products
    product_count = category.products.count()
    if product_count > 0:
        messages.error(request, f"Impossible de supprimer: {product_count} produit(s) utilisent cette catégorie.")
        return redirect('products:category_list')

    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Catégorie '{name}' supprimée avec succès.")

    return redirect('products:category_list')


# Rôle : inverse is_active de la catégorie sur POST, puis revient à la liste.
# Liens : route /products/categories/<pk>/toggle/, formulaire de category_list.html ; écrit Category.
@login_required
@role_required('admin', 'owner', 'manager')
def category_toggle(request, pk):
    """Toggle category active status"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    category = get_object_or_404(Category, pk=pk)

    # Check access
    if enterprise and category.enterprise and category.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette catégorie.")
        return redirect('products:category_list')

    if request.method == 'POST':
        category.is_active = not category.is_active
        category.save()

        status = "activée" if category.is_active else "désactivée"
        messages.success(request, f"Catégorie '{category.name}' {status}.")

    return redirect('products:category_list')


# =============================================================================
# PRODUCT VIEWS
# =============================================================================

# Rôle : liste les produits et leurs emplacements en stock, avec filtres, pagination et export PDF/Excel.
# Liens : route /products/, menu de templates/base.html ; lit Stock (apps/stock/models.py) et LocationStock.
# Appelle export_list_response (apps/core/exports.py) ; rend product_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager')
def product_list(request):
    """List all products"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    # Prefetch the locations that actually hold each product (quantity > 0),
    # so the list can show an "Emplacements" column without N+1 queries.
    location_stock_qs = (
        LocationStock.objects.filter(quantity__gt=0)
        .select_related('location')
        .order_by('location__name')
    )

    # Get products with stock info
    products = Product.objects.select_related('category').prefetch_related(
        Prefetch('location_stocks', queryset=location_stock_qs, to_attr='active_location_stocks')
    ).order_by('name')

    if enterprise:
        products = products.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Get categories for filter
    categories = Category.objects.filter(is_active=True)
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Get locations (emplacements) for filter
    locations = Location.objects.filter(is_active=True).order_by('name')
    if enterprise:
        locations = locations.filter(enterprise=enterprise)

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category_id=category_filter)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)
    elif status_filter == 'popular':
        products = products.filter(is_popular=True)

    # Filter by emplacement (location): products holding stock at that location
    location_filter = request.GET.get('location')
    if location_filter:
        products = products.filter(
            location_stocks__location_id=location_filter,
            location_stocks__quantity__gt=0,
        ).distinct()

    # Filter by stock level
    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        # Products with stock below threshold
        low_stock_products = Stock.objects.filter(
            quantity__lt=models.F('product__min_stock_threshold')
        ).values_list('product_id', flat=True)
        products = products.filter(id__in=low_stock_products)
    elif stock_filter == 'out':
        # Products with zero stock
        zero_stock = Stock.objects.filter(quantity=0).values_list('product_id', flat=True)
        products = products.filter(id__in=zero_stock)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(barcode__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    # Export (respects the active filters, before pagination)
    from apps.core.exports import export_list_response, fmt_qty
    export = export_list_response(
        request,
        title="Liste des Produits",
        headers=["Produit", "Catégorie", "SKU", "Code-barres", "Prix d'achat", "Prix de vente",
                 "Unité", "Seuil min", "Emplacements (stock > 0)", "Statut"],
        rows=(
            [
                p.name,
                p.category.name if p.category else '',
                p.sku or '',
                p.barcode or '',
                float(p.purchase_price or 0),
                float(p.sale_price or 0),
                p.unit,
                fmt_qty(p.min_stock_threshold),
                ', '.join(
                    f"{ls.location.name} ({fmt_qty(ls.quantity)})"
                    for ls in getattr(p, 'active_location_stocks', [])
                ),
                'Actif' if p.is_active else 'Inactif',
            ]
            for p in products
        ),
        filename="produits",
    )
    if export:
        return export

    # Pagination
    paginator = Paginator(products, 25)
    page = request.GET.get('page', 1)
    products = paginator.get_page(page)

    # Stats
    total_products = Product.objects.count()
    if enterprise:
        total_products = Product.objects.filter(
            Q(enterprise=enterprise) | Q(enterprise__isnull=True)
        ).count()
    active_products = Product.objects.filter(is_active=True).count()

    context = {
        'products': products,
        'categories': categories,
        'locations': locations,
        'selected_category': category_filter,
        'selected_status': status_filter,
        'selected_stock': stock_filter,
        'selected_location': location_filter,
        'search': search,
        'total_products': total_products,
        'active_products': active_products,
    }
    return render(request, 'products/product_list.html', context)


# Rôle : valide le formulaire, crée le produit et une ligne Stock initiale à quantité 0.
# Liens : route /products/create/, liens dans product_list.html et apps/stock/templates/stock/entry.html.
# Écrit Product (apps/products/models.py) et Stock (apps/stock/models.py).
@login_required
@role_required('admin', 'owner', 'manager')
def product_create(request):
    """Create a new product"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    # Get categories for dropdown
    categories = Category.objects.filter(is_active=True).order_by('name')
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        barcode = request.POST.get('barcode', '').strip() or None
        sku = request.POST.get('sku', '').strip() or None
        unit = request.POST.get('unit', 'piece')
        purchase_price = request.POST.get('purchase_price', '0')
        sale_price = request.POST.get('sale_price', '0')
        tax_rate = request.POST.get('tax_rate', '0')
        min_stock_threshold = request.POST.get('min_stock_threshold', '0')
        is_popular = request.POST.get('is_popular') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # Validate
        errors = []

        if not name:
            errors.append("Le nom du produit est requis.")

        if not category_id:
            errors.append("La catégorie est requise.")

        try:
            purchase_price = float(purchase_price or 0)
            sale_price = float(sale_price or 0)
            tax_rate = float(tax_rate or 0)
            min_stock_threshold = int(min_stock_threshold or 0)
        except (ValueError, TypeError):
            errors.append("Les valeurs numériques sont invalides.")
            purchase_price = None
            sale_price = None

        if purchase_price is not None and sale_price is not None:
            if purchase_price < 0 or sale_price < 0:
                errors.append("Les prix ne peuvent pas être négatifs.")

        if barcode and Product.objects.filter(barcode=barcode).exists():
            errors.append("Un produit avec ce code-barres existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'mode': 'create',
                'categories': categories,
                'unit_choices': Product.UNIT_CHOICES,
                'form_data': request.POST,
            }
            return render(request, 'products/product_form.html', context)
        else:
            category = get_object_or_404(Category, pk=category_id)

            product = Product.objects.create(
                name=name,
                category=category,
                description=description,
                barcode=barcode,
                sku=sku,
                unit=unit,
                purchase_price=purchase_price,
                sale_price=sale_price,
                tax_rate=tax_rate,
                min_stock_threshold=min_stock_threshold,
                is_popular=is_popular,
                is_active=is_active,
                enterprise=enterprise,
            )

            # Create initial stock record
            Stock.objects.get_or_create(
                product=product,
                defaults={'quantity': 0}
            )

            messages.success(request, f"Produit '{product.name}' créé avec succès.")
            return redirect('products:product_list')

    context = {
        'mode': 'create',
        'categories': categories,
        'unit_choices': Product.UNIT_CHOICES,
    }
    return render(request, 'products/product_form.html', context)


# Rôle : affiche un produit avec son stock par emplacement et le total, sommé depuis les lignes Stock.
# Liens : route /products/<pk>/, liée depuis les listes et tableaux de bord ; rend product_detail.html.
@login_required
@role_required('admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager')
def product_detail(request, pk):
    """View product details"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)

    # Check access
    if enterprise and product.enterprise and product.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce produit.")
        return redirect('products:product_list')

    # Stock is tracked per emplacement (multi-location). Show the breakdown
    # across locations plus the total, instead of one arbitrary Stock row.
    stock_rows = (
        Stock.objects.filter(product=product)
        .select_related('location')
        .order_by('location__name')
    )
    total_stock = stock_rows.aggregate(total=Sum('quantity'))['total'] or 0

    context = {
        'product': product,
        'stock_rows': stock_rows,
        'total_stock': total_stock,
    }
    return render(request, 'products/product_detail.html', context)


# Rôle : modifie un produit de l'entreprise avec les mêmes contrôles que la création, sans toucher au stock.
# Liens : route /products/<pk>/edit/, liens dans product_list.html et product_detail.html ; rend le formulaire.
@login_required
@role_required('admin', 'owner', 'manager')
def product_edit(request, pk):
    """Edit a product"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)

    # Check access
    if enterprise and product.enterprise and product.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce produit.")
        return redirect('products:product_list')

    # Get categories for dropdown
    categories = Category.objects.filter(is_active=True).order_by('name')
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        description = request.POST.get('description', '').strip()
        barcode = request.POST.get('barcode', '').strip() or None
        sku = request.POST.get('sku', '').strip() or None
        unit = request.POST.get('unit', 'piece')
        purchase_price = request.POST.get('purchase_price', '0')
        sale_price = request.POST.get('sale_price', '0')
        tax_rate = request.POST.get('tax_rate', '0')
        min_stock_threshold = request.POST.get('min_stock_threshold', '0')
        is_popular = request.POST.get('is_popular') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        # Validate
        errors = []

        if not name:
            errors.append("Le nom du produit est requis.")

        if not category_id:
            errors.append("La catégorie est requise.")

        try:
            purchase_price = float(purchase_price or 0)
            sale_price = float(sale_price or 0)
            tax_rate = float(tax_rate or 0)
            min_stock_threshold = int(min_stock_threshold or 0)
        except (ValueError, TypeError):
            errors.append("Les valeurs numériques sont invalides.")
            purchase_price = None
            sale_price = None

        if purchase_price is not None and sale_price is not None:
            if purchase_price < 0 or sale_price < 0:
                errors.append("Les prix ne peuvent pas être négatifs.")

        if barcode and Product.objects.filter(barcode=barcode).exclude(pk=pk).exists():
            errors.append("Un produit avec ce code-barres existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            category = get_object_or_404(Category, pk=category_id)

            product.name = name
            product.category = category
            product.description = description
            product.barcode = barcode
            product.sku = sku
            product.unit = unit
            product.purchase_price = purchase_price
            product.sale_price = sale_price
            product.tax_rate = tax_rate
            product.min_stock_threshold = min_stock_threshold
            product.is_popular = is_popular
            product.is_active = is_active
            product.save()

            messages.success(request, f"Produit '{product.name}' modifié avec succès.")
            return redirect('products:product_list')

    context = {
        'mode': 'edit',
        'product': product,
        'categories': categories,
        'unit_choices': Product.UNIT_CHOICES,
    }
    return render(request, 'products/product_form.html', context)


# Rôle : inverse is_active du produit sur POST, puis revient à la liste.
# Liens : route /products/<pk>/toggle/, formulaires de product_list.html et product_detail.html ; écrit Product.
@login_required
@role_required('admin', 'owner', 'manager')
def product_toggle(request, pk):
    """Toggle product active status"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    product = get_object_or_404(Product, pk=pk)

    # Check access
    if enterprise and product.enterprise and product.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce produit.")
        return redirect('products:product_list')

    if request.method == 'POST':
        product.is_active = not product.is_active
        product.save()

        status = "activé" if product.is_active else "désactivé"
        messages.success(request, f"Produit '{product.name}' {status}.")

    return redirect('products:product_list')


# Rôle : sur POST, désactive le produit s'il a des ventes ou mouvements, sinon le supprime définitivement.
# Liens : route /products/<pk>/delete/, appelée dans tests/test_forms_e2e.py ; aucun template ne la référence.
# Lit SaleItem (apps/pos/models.py) et StockMovement (apps/stock/models.py).
@login_required
@role_required('admin', 'owner', 'manager')
def product_delete(request, pk):
    """Delete a product (soft delete by deactivating)"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    product = get_object_or_404(Product, pk=pk)

    # Check access
    if enterprise and product.enterprise and product.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce produit.")
        return redirect('products:product_list')

    if request.method == 'POST':
        # Check if product has stock movements or sales
        from apps.pos.models import SaleItem
        from apps.stock.models import StockMovement

        has_sales = SaleItem.objects.filter(product=product).exists()
        has_movements = StockMovement.objects.filter(product=product).exists()

        if has_sales or has_movements:
            # Soft delete - just deactivate
            product.is_active = False
            product.save()
            messages.warning(request, f"Produit '{product.name}' désactivé (historique conservé).")
        else:
            # Hard delete - no history
            name = product.name
            product.delete()
            messages.success(request, f"Produit '{name}' supprimé définitivement.")

    return redirect('products:product_list')
