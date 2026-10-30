"""
Frontend views for Customer Management
"""
from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal

from .models import Customer, CustomerCredit, CreditPayment
from apps.pos.models import Sale


# Rôle : fabrique un décorateur de vue qui limite l'accès aux rôles donnés.
# Liens : appliqué aux vues d'ici ; même logique dans apps/accounting/views.py et apps/products/views.py.
def role_required(*roles):
    """Decorator to check if user has required role"""
    # Rôle : reçoit la vue à protéger et renvoie wrapper, en gardant ses métadonnées grâce à @wraps.
    # Liens : utilisé uniquement par role_required, dans ce fichier.
    def decorator(view_func):
        # Rôle : renvoie l'anonyme vers login et le mauvais rôle vers home avec un message, sinon exécute la vue.
        # Liens : routes login et home de stock_control/urls.py ; lit User.role (apps/accounts/models.py).
        @wraps(view_func)
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
# CUSTOMER VIEWS
# =============================================================================

# Rôle : liste les clients avec filtres (statut, dette), recherche, statistiques de crédit et export PDF/Excel.
# Liens : route /customers/, menu de templates/base.html ; appelle export_list_response (apps/core/exports.py).
# Rend customer_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def customer_list(request):
    """List all customers"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    customers = Customer.objects.order_by('-created_at')
    if enterprise:
        customers = customers.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)
    elif status_filter == 'credit':
        customers = customers.filter(current_balance__gt=0)

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        customers = customers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    # Export (respects the active filters, before pagination)
    from apps.core.exports import export_list_response
    export = export_list_response(
        request,
        title="Liste des Clients",
        headers=["Client", "Téléphone", "Email", "Total achats", "Crédit en cours", "Statut", "Créé le"],
        rows=(
            [
                c.name,
                c.phone or '',
                c.email or '',
                float(c.total_purchases or 0),
                float(c.current_balance or 0),
                'Actif' if c.is_active else 'Inactif',
                c.created_at,
            ]
            for c in customers
        ),
        filename="clients",
    )
    if export:
        return export

    # Pagination
    paginator = Paginator(customers, 25)
    page = request.GET.get('page', 1)
    customers = paginator.get_page(page)

    # Stats
    all_customers = Customer.objects.all()
    if enterprise:
        all_customers = all_customers.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    total_customers = all_customers.count()
    active_customers = all_customers.filter(is_active=True).count()
    customers_with_credit = all_customers.filter(current_balance__gt=0).count()
    total_credit = all_customers.aggregate(total=Sum('current_balance'))['total'] or 0

    context = {
        'customers': customers,
        'selected_status': status_filter,
        'search': search,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'customers_with_credit': customers_with_credit,
        'total_credit': total_credit,
    }
    return render(request, 'customers/customer_list.html', context)


# Rôle : crée un client ; refuse un téléphone ou un email déjà pris dans l'entreprise, ou une limite négative.
# Liens : route /customers/create/, lien depuis customer_list.html ; écrit Customer ; rend customer_form.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier')
def customer_create(request):
    """Create a new customer"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip() or None
        email = request.POST.get('email', '').strip() or None
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()
        credit_limit = request.POST.get('credit_limit', '0')

        # Validate
        errors = []

        if not name:
            errors.append("Le nom du client est requis.")

        if phone and Customer.objects.filter(phone=phone, enterprise=enterprise).exists():
            errors.append("Un client avec ce numéro de téléphone existe déjà.")

        if email and Customer.objects.filter(email=email, enterprise=enterprise).exists():
            errors.append("Un client avec cet email existe déjà.")

        try:
            credit_limit = Decimal(credit_limit or '0')
            if credit_limit < 0:
                errors.append("La limite de crédit ne peut pas être négative.")
        except:
            errors.append("Limite de crédit invalide.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'mode': 'create',
                'form_data': request.POST,
            }
            return render(request, 'customers/customer_form.html', context)
        else:
            customer = Customer.objects.create(
                name=name,
                phone=phone,
                email=email,
                address=address,
                notes=notes,
                credit_limit=credit_limit,
                enterprise=enterprise,
            )
            messages.success(request, f"Client '{customer.name}' créé avec succès.")
            return redirect('customers:customer_list')

    return render(request, 'customers/customer_form.html', {'mode': 'create'})


# Rôle : affiche un client avec ses crédits, ses 10 dernières ventes et ses 20 derniers paiements.
# Liens : route /customers/<pk>/ ; lit CustomerCredit, CreditPayment et Sale (apps/pos/models.py).
# Rend customer_detail.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def customer_detail(request, pk):
    """View customer details with credits and purchase history"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    customer = get_object_or_404(Customer, pk=pk)

    # Check access
    if enterprise and customer.enterprise and customer.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce client.")
        return redirect('customers:customer_list')

    # Get customer credits
    credits = CustomerCredit.objects.filter(customer=customer).order_by('-created_at')
    pending_credits = credits.filter(status__in=['pending', 'partial'])

    # Get recent sales
    recent_sales = Sale.objects.filter(customer=customer).order_by('-created_at')[:10]

    # Get credit payments
    credit_payments = CreditPayment.objects.filter(
        credit__customer=customer
    ).order_by('-created_at')[:20]

    context = {
        'customer': customer,
        'credits': credits,
        'pending_credits': pending_credits,
        'recent_sales': recent_sales,
        'credit_payments': credit_payments,
    }
    return render(request, 'customers/customer_detail.html', context)


# Rôle : modifie un client avec les mêmes contrôles que la création, en excluant le client lui-même.
# Liens : route /customers/<pk>/edit/ ; Customer.save() déclenche le contrôle de apps/customers/signals.py.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager')
def customer_edit(request, pk):
    """Edit a customer"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    customer = get_object_or_404(Customer, pk=pk)

    # Check access
    if enterprise and customer.enterprise and customer.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce client.")
        return redirect('customers:customer_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip() or None
        email = request.POST.get('email', '').strip() or None
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()
        credit_limit = request.POST.get('credit_limit', '0')
        is_active = request.POST.get('is_active') == 'on'

        # Validate
        errors = []

        if not name:
            errors.append("Le nom du client est requis.")

        if phone and Customer.objects.filter(phone=phone, enterprise=enterprise).exclude(pk=pk).exists():
            errors.append("Un client avec ce numéro de téléphone existe déjà.")

        if email and Customer.objects.filter(email=email, enterprise=enterprise).exclude(pk=pk).exists():
            errors.append("Un client avec cet email existe déjà.")

        try:
            credit_limit = Decimal(credit_limit or '0')
            if credit_limit < 0:
                errors.append("La limite de crédit ne peut pas être négative.")
        except:
            errors.append("Limite de crédit invalide.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            customer.name = name
            customer.phone = phone
            customer.email = email
            customer.address = address
            customer.notes = notes
            customer.credit_limit = credit_limit
            customer.is_active = is_active
            customer.save()

            messages.success(request, f"Client '{customer.name}' modifié avec succès.")
            return redirect('customers:customer_detail', pk=customer.pk)

    context = {
        'mode': 'edit',
        'customer': customer,
    }
    return render(request, 'customers/customer_form.html', context)


# Rôle : inverse is_active du client sur POST (suppression logique), sans effacer la ligne.
# Liens : route /customers/<pk>/toggle/, formulaire de customer_detail.html ; redirige vers customer_list.
@login_required
@role_required('admin', 'owner', 'manager')
def customer_toggle(request, pk):
    """Toggle customer active status"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    customer = get_object_or_404(Customer, pk=pk)

    # Check access
    if enterprise and customer.enterprise and customer.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce client.")
        return redirect('customers:customer_list')

    if request.method == 'POST':
        customer.is_active = not customer.is_active
        customer.save()

        status = "activé" if customer.is_active else "désactivé"
        messages.success(request, f"Client '{customer.name}' {status}.")

    return redirect('customers:customer_list')


# =============================================================================
# CREDIT & PAYMENT VIEWS
# =============================================================================

# Rôle : liste les crédits de l'entreprise avec filtres (statut, retard, nom), totaux et export PDF/Excel.
# Liens : route /customers/credits/, menu de templates/base.html, apps/core/dashboard_views.py.
# Appelle export_list_response (apps/core/exports.py) ; rend credit_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def credit_list(request):
    """List all customer credits"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    credits = CustomerCredit.objects.select_related('customer', 'sale').order_by('-created_at')
    if enterprise:
        credits = credits.filter(customer__enterprise=enterprise)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter in ['pending', 'partial', 'paid']:
        credits = credits.filter(status=status_filter)

    # Filter by overdue
    if request.GET.get('overdue') == 'true':
        from datetime import date
        credits = credits.filter(
            due_date__lt=date.today(),
            status__in=['pending', 'partial']
        )

    # Search by customer name
    search = request.GET.get('search', '').strip()
    if search:
        credits = credits.filter(customer__name__icontains=search)

    # Export (respects the active filters, before pagination)
    from apps.core.exports import export_list_response
    status_labels = {'pending': 'En attente', 'partial': 'Partiellement payé', 'paid': 'Payé'}
    export = export_list_response(
        request,
        title="Crédits Clients",
        headers=["Client", "Téléphone", "N° Vente", "Montant initial", "Restant dû", "Statut", "Échéance", "Créé le"],
        rows=(
            [
                cr.customer.name,
                cr.customer.phone or '',
                cr.sale.sale_number if cr.sale_id else '',
                float(cr.original_amount or 0),
                float(cr.remaining_amount or 0),
                status_labels.get(cr.status, cr.status),
                cr.due_date,
                cr.created_at,
            ]
            for cr in credits
        ),
        filename="credits_clients",
    )
    if export:
        return export

    # Pagination
    paginator = Paginator(credits, 25)
    page = request.GET.get('page', 1)
    credits = paginator.get_page(page)

    # Stats
    all_credits = CustomerCredit.objects.all()
    if enterprise:
        all_credits = all_credits.filter(customer__enterprise=enterprise)

    total_pending = all_credits.filter(status__in=['pending', 'partial']).aggregate(
        total=Sum('remaining_amount')
    )['total'] or 0

    overdue_count = 0
    from datetime import date
    overdue_count = all_credits.filter(
        due_date__lt=date.today(),
        status__in=['pending', 'partial']
    ).count()

    context = {
        'credits': credits,
        'selected_status': status_filter,
        'search': search,
        'is_overdue_filter': request.GET.get('overdue') == 'true',
        'total_pending': total_pending,
        'overdue_count': overdue_count,
    }
    return render(request, 'customers/credit_list.html', context)


# Rôle : valide un paiement (positif, au plus le reste dû) et crée le CreditPayment ; refuse un crédit soldé.
# Liens : route /customers/credits/<credit_id>/pay/ ; CreditPayment.save() met à jour crédit et solde client.
# Liens depuis credit_list.html et customer_detail.html ; rend record_payment.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier')
def record_payment(request, credit_id):
    """Record a payment for a credit"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    credit = get_object_or_404(CustomerCredit.objects.select_related('customer'), pk=credit_id)

    # Check access
    if enterprise and credit.customer.enterprise and credit.customer.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce crédit.")
        return redirect('customers:credit_list')

    if credit.status == 'paid':
        messages.warning(request, "Ce crédit est déjà payé.")
        return redirect('customers:customer_detail', pk=credit.customer.pk)

    if request.method == 'POST':
        amount = request.POST.get('amount', '0')
        payment_method = request.POST.get('payment_method', 'cash')
        payment_reference = request.POST.get('payment_reference', '').strip()
        notes = request.POST.get('notes', '').strip()

        # Validate
        errors = []

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Le montant doit être positif.")
            if amount > credit.remaining_amount:
                errors.append(f"Le montant ne peut pas dépasser {credit.remaining_amount} FB.")
        except:
            errors.append("Montant invalide.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            CreditPayment.objects.create(
                credit=credit,
                user=user,
                amount=amount,
                payment_method=payment_method,
                payment_reference=payment_reference,
                notes=notes,
            )

            messages.success(request, f"Paiement de {amount} FB enregistré avec succès.")
            return redirect('customers:customer_detail', pk=credit.customer.pk)

    context = {
        'credit': credit,
        'customer': credit.customer,
        'payment_methods': CreditPayment.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'customers/record_payment.html', context)


# Rôle : liste paginée des paiements de crédit d'un client, avec le total déjà versé.
# Liens : route /customers/<customer_id>/payments/, lien dans customer_detail.html ; rend payment_history.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def payment_history(request, customer_id):
    """View payment history for a customer"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    customer = get_object_or_404(Customer, pk=customer_id)

    # Check access
    if enterprise and customer.enterprise and customer.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à ce client.")
        return redirect('customers:customer_list')

    payments = CreditPayment.objects.filter(
        credit__customer=customer
    ).select_related('credit', 'user').order_by('-created_at')

    # Pagination
    paginator = Paginator(payments, 25)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)

    # Stats
    total_paid = CreditPayment.objects.filter(
        credit__customer=customer
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'customer': customer,
        'payments': payments,
        'total_paid': total_paid,
    }
    return render(request, 'customers/payment_history.html', context)
