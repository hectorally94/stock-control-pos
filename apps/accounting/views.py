"""
Frontend views for Accounting (Expenses, Cash Register Sessions)
"""
from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal

from .models import Expense, ExpenseCategory, CashRegisterSession, DailySummary
from apps.locations.models import Location


# Rôle : fabrique un décorateur de vue qui limite l'accès aux rôles donnés.
# Liens : appliqué aux vues d'ici ; même logique dans apps/customers/views.py et apps/products/views.py.
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
# EXPENSE CATEGORY VIEWS
# =============================================================================

# Rôle : liste les catégories de l'entreprise et les globales, avec le nombre et le total de leurs dépenses.
# Liens : route /accounting/expense-categories/, lien dans expense_list.html ; rend expense_category_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'accountant')
def expense_category_list(request):
    """List all expense categories"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    categories = ExpenseCategory.objects.order_by('name')
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    # Stats
    for cat in categories:
        cat.expense_count = cat.expenses.count()
        cat.total_amount = cat.expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'categories': categories,
    }
    return render(request, 'accounting/expense_category_list.html', context)


# Rôle : crée une catégorie de dépense après contrôle du nom (requis, unique dans l'entreprise).
# Liens : route /accounting/expense-categories/create/ ; rend expense_category_form.html ; écrit ce modèle.
@login_required
@role_required('admin', 'owner', 'manager')
def expense_category_create(request):
    """Create a new expense category"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

        errors = []
        if not name:
            errors.append("Le nom de la catégorie est requis.")

        if ExpenseCategory.objects.filter(name__iexact=name, enterprise=enterprise).exists():
            errors.append("Une catégorie avec ce nom existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {'mode': 'create', 'form_data': request.POST}
            return render(request, 'accounting/expense_category_form.html', context)

        ExpenseCategory.objects.create(
            name=name,
            description=description,
            enterprise=enterprise,
        )
        messages.success(request, f"Catégorie '{name}' créée avec succès.")
        return redirect('accounting:expense_category_list')

    return render(request, 'accounting/expense_category_form.html', {'mode': 'create'})


# Rôle : modifie le nom, la description et l'état actif d'une catégorie de la même entreprise.
# Liens : route /accounting/expense-categories/<pk>/edit/ ; partage expense_category_form.html avec la création.
@login_required
@role_required('admin', 'owner', 'manager')
def expense_category_edit(request, pk):
    """Edit an expense category"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    category = get_object_or_404(ExpenseCategory, pk=pk)

    if enterprise and category.enterprise and category.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette catégorie.")
        return redirect('accounting:expense_category_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = []
        if not name:
            errors.append("Le nom de la catégorie est requis.")

        if ExpenseCategory.objects.filter(name__iexact=name, enterprise=enterprise).exclude(pk=pk).exists():
            errors.append("Une catégorie avec ce nom existe déjà.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            category.name = name
            category.description = description
            category.is_active = is_active
            category.save()

            messages.success(request, f"Catégorie '{name}' modifiée avec succès.")
            return redirect('accounting:expense_category_list')

    context = {
        'mode': 'edit',
        'category': category,
    }
    return render(request, 'accounting/expense_category_form.html', context)


# =============================================================================
# EXPENSE VIEWS
# =============================================================================

# Rôle : liste les dépenses avec filtres (catégorie, paiement, période, recherche), totaux et export PDF/Excel.
# Liens : route /accounting/expenses/, menu de templates/base.html, apps/core/dashboard_views.py.
# Appelle export_list_response (apps/core/exports.py) ; rend expense_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'accountant')
def expense_list(request):
    """List all expenses"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    expenses = Expense.objects.select_related('expense_category', 'location', 'user').order_by('-expense_date', '-created_at')
    if enterprise:
        expenses = expenses.filter(enterprise=enterprise)

    # Filter by category
    category_filter = request.GET.get('category')
    if category_filter:
        expenses = expenses.filter(expense_category_id=category_filter)

    # Filter by payment method
    payment_filter = request.GET.get('payment')
    if payment_filter:
        expenses = expenses.filter(payment_method=payment_filter)

    # Filter by date range
    date_filter = request.GET.get('date')
    today = date.today()
    if date_filter == 'today':
        expenses = expenses.filter(expense_date=today)
    elif date_filter == 'week':
        start_week = today - timedelta(days=today.weekday())
        expenses = expenses.filter(expense_date__gte=start_week)
    elif date_filter == 'month':
        expenses = expenses.filter(expense_date__year=today.year, expense_date__month=today.month)

    # Date range (?start=YYYY-MM-DD&end=YYYY-MM-DD) — used by dashboard drill-downs
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start and end:
        try:
            start_d = datetime.strptime(start, '%Y-%m-%d').date()
            end_d = datetime.strptime(end, '%Y-%m-%d').date()
            expenses = expenses.filter(expense_date__gte=start_d, expense_date__lte=end_d)
        except ValueError:
            pass

    # Search
    search = request.GET.get('search', '').strip()
    if search:
        expenses = expenses.filter(
            Q(description__icontains=search) |
            Q(supplier__icontains=search) |
            Q(reference__icontains=search)
        )

    # Export (respects the active filters, before pagination)
    from apps.core.exports import export_list_response
    export = export_list_response(
        request,
        title="Liste des Dépenses",
        headers=["Date", "Description", "Catégorie", "Montant", "Paiement", "Fournisseur",
                 "Référence", "Emplacement", "Par"],
        rows=(
            [
                e.expense_date,
                e.description,
                e.expense_category.name if e.expense_category else '',
                float(e.amount or 0),
                e.get_payment_method_display(),
                e.supplier or '',
                e.reference or '',
                e.location.name if e.location else '',
                e.user.get_full_name() or e.user.username if e.user else '',
            ]
            for e in expenses
        ),
        filename="depenses",
    )
    if export:
        return export

    # Pagination
    paginator = Paginator(expenses, 25)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)

    # Stats
    all_expenses = Expense.objects.all()
    if enterprise:
        all_expenses = all_expenses.filter(enterprise=enterprise)

    total_expenses = all_expenses.aggregate(total=Sum('amount'))['total'] or 0
    today_expenses = all_expenses.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or 0
    month_expenses = all_expenses.filter(expense_date__year=today.year, expense_date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0

    # Categories for filter
    categories = ExpenseCategory.objects.filter(is_active=True)
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    context = {
        'expenses': expenses,
        'categories': categories,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
        'selected_category': category_filter,
        'selected_payment': payment_filter,
        'selected_date': date_filter,
        'search': search,
        'total_expenses': total_expenses,
        'today_expenses': today_expenses,
        'month_expenses': month_expenses,
    }
    return render(request, 'accounting/expense_list.html', context)


# Rôle : valide le formulaire (description, montant positif, date) puis crée la dépense au nom de l'utilisateur.
# Liens : route /accounting/expenses/create/, lien dans expense_list.html ; écrit Expense via expense_form.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'accountant')
def expense_create(request):
    """Create a new expense"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    categories = ExpenseCategory.objects.filter(is_active=True)
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    locations = Location.objects.filter(is_active=True)
    if enterprise:
        locations = locations.filter(enterprise=enterprise)

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '0')
        expense_date = request.POST.get('expense_date', '')
        category_id = request.POST.get('category', '')
        location_id = request.POST.get('location', '')
        payment_method = request.POST.get('payment_method', 'cash')
        supplier = request.POST.get('supplier', '').strip()
        reference = request.POST.get('reference', '').strip()
        is_recurring = request.POST.get('is_recurring') == 'on'
        notes = request.POST.get('notes', '').strip()

        errors = []

        if not description:
            errors.append("La description est requise.")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Le montant doit être positif.")
        except:
            errors.append("Montant invalide.")

        if not expense_date:
            errors.append("La date de la dépense est requise.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'mode': 'create',
                'form_data': request.POST,
                'categories': categories,
                'locations': locations,
                'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
            }
            return render(request, 'accounting/expense_form.html', context)

        expense = Expense.objects.create(
            description=description,
            amount=amount,
            expense_date=expense_date,
            expense_category_id=category_id if category_id else None,
            location_id=location_id if location_id else None,
            payment_method=payment_method,
            supplier=supplier or None,
            reference=reference or None,
            is_recurring=is_recurring,
            notes=notes or None,
            user=user,
            enterprise=enterprise,
        )

        messages.success(request, f"Dépense de {amount} FB enregistrée avec succès.")
        return redirect('accounting:expense_list')

    context = {
        'mode': 'create',
        'categories': categories,
        'locations': locations,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
        'today': date.today().isoformat(),
    }
    return render(request, 'accounting/expense_form.html', context)


# Rôle : affiche une dépense, après contrôle qu'elle appartient à l'entreprise de l'utilisateur.
# Liens : route /accounting/expenses/<pk>/ ; rend expense_detail.html ; cible de redirection de expense_edit.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'accountant')
def expense_detail(request, pk):
    """View expense details"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    expense = get_object_or_404(Expense.objects.select_related('expense_category', 'location', 'user'), pk=pk)

    if enterprise and expense.enterprise and expense.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette dépense.")
        return redirect('accounting:expense_list')

    context = {
        'expense': expense,
    }
    return render(request, 'accounting/expense_detail.html', context)


# Rôle : applique les mêmes contrôles que la création puis met à jour la dépense existante.
# Liens : route /accounting/expenses/<pk>/edit/ ; partage expense_form.html avec expense_create.
@login_required
@role_required('admin', 'owner', 'manager', 'accountant')
def expense_edit(request, pk):
    """Edit an expense"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    expense = get_object_or_404(Expense, pk=pk)

    if enterprise and expense.enterprise and expense.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette dépense.")
        return redirect('accounting:expense_list')

    categories = ExpenseCategory.objects.filter(is_active=True)
    if enterprise:
        categories = categories.filter(Q(enterprise=enterprise) | Q(enterprise__isnull=True))

    locations = Location.objects.filter(is_active=True)
    if enterprise:
        locations = locations.filter(enterprise=enterprise)

    if request.method == 'POST':
        description = request.POST.get('description', '').strip()
        amount = request.POST.get('amount', '0')
        expense_date = request.POST.get('expense_date', '')
        category_id = request.POST.get('category', '')
        location_id = request.POST.get('location', '')
        payment_method = request.POST.get('payment_method', 'cash')
        supplier = request.POST.get('supplier', '').strip()
        reference = request.POST.get('reference', '').strip()
        is_recurring = request.POST.get('is_recurring') == 'on'
        notes = request.POST.get('notes', '').strip()

        errors = []

        if not description:
            errors.append("La description est requise.")

        try:
            amount = Decimal(amount)
            if amount <= 0:
                errors.append("Le montant doit être positif.")
        except:
            errors.append("Montant invalide.")

        if not expense_date:
            errors.append("La date de la dépense est requise.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            expense.description = description
            expense.amount = amount
            expense.expense_date = expense_date
            expense.expense_category_id = category_id if category_id else None
            expense.location_id = location_id if location_id else None
            expense.payment_method = payment_method
            expense.supplier = supplier or None
            expense.reference = reference or None
            expense.is_recurring = is_recurring
            expense.notes = notes or None
            expense.save()

            messages.success(request, "Dépense modifiée avec succès.")
            return redirect('accounting:expense_detail', pk=expense.pk)

    context = {
        'mode': 'edit',
        'expense': expense,
        'categories': categories,
        'locations': locations,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'accounting/expense_form.html', context)


# Rôle : supprime définitivement la dépense sur POST ; un GET renvoie simplement vers son détail.
# Liens : route /accounting/expenses/<pk>/delete/, formulaire de expense_detail.html ; supprime l'Expense.
@login_required
@role_required('admin', 'owner', 'manager')
def expense_delete(request, pk):
    """Delete an expense"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    expense = get_object_or_404(Expense, pk=pk)

    if enterprise and expense.enterprise and expense.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette dépense.")
        return redirect('accounting:expense_list')

    if request.method == 'POST':
        expense.delete()
        messages.success(request, "Dépense supprimée avec succès.")
        return redirect('accounting:expense_list')

    return redirect('accounting:expense_detail', pk=pk)


# =============================================================================
# CASH REGISTER SESSION VIEWS
# =============================================================================

# Rôle : liste les sessions de caisse avec filtres et statistiques ; un caissier ne voit que les siennes.
# Liens : route /accounting/cash-sessions/, menu de templates/base.html, apps/core/dashboard_views.py.
# Lit CashRegisterSession (apps/accounting/models.py) ; rend cash_session_list.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def cash_session_list(request):
    """List all cash register sessions"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    sessions = CashRegisterSession.objects.select_related('user', 'location').order_by('-opened_at')
    if enterprise:
        sessions = sessions.filter(enterprise=enterprise)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    # Filter by user (for managers)
    user_filter = request.GET.get('user')
    if user_filter:
        sessions = sessions.filter(user_id=user_filter)

    # Cashiers can only see their own sessions
    if user.role == 'cashier':
        sessions = sessions.filter(user=user)

    # Pagination
    paginator = Paginator(sessions, 25)
    page = request.GET.get('page', 1)
    sessions = paginator.get_page(page)

    # Stats
    all_sessions = CashRegisterSession.objects.all()
    if enterprise:
        all_sessions = all_sessions.filter(enterprise=enterprise)
    if user.role == 'cashier':
        all_sessions = all_sessions.filter(user=user)

    open_sessions = all_sessions.filter(status='open').count()
    total_difference = all_sessions.filter(status='closed').aggregate(total=Sum('difference'))['total'] or 0

    context = {
        'sessions': sessions,
        'selected_status': status_filter,
        'open_sessions': open_sessions,
        'total_difference': total_difference,
    }
    return render(request, 'accounting/cash_session_list.html', context)


# Rôle : ouvre une session avec un solde initial ; si l'utilisateur en a déjà une ouverte, redirige vers elle.
# Liens : route /accounting/cash-sessions/open/, lien depuis cash_session_list.html ; écrit CashRegisterSession.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier')
def cash_session_open(request):
    """Open a new cash register session"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    # Check if user already has an open session
    existing_session = CashRegisterSession.objects.filter(user=user, status='open').first()
    if existing_session:
        messages.warning(request, "Vous avez déjà une session ouverte.")
        return redirect('accounting:cash_session_detail', pk=existing_session.pk)

    locations = Location.objects.filter(is_active=True)
    if enterprise:
        locations = locations.filter(enterprise=enterprise)

    if request.method == 'POST':
        opening_balance = request.POST.get('opening_balance', '0')
        location_id = request.POST.get('location', '')
        notes = request.POST.get('notes', '').strip()

        errors = []

        try:
            opening_balance = Decimal(opening_balance)
            if opening_balance < 0:
                errors.append("Le solde d'ouverture ne peut pas être négatif.")
        except:
            errors.append("Montant invalide.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'locations': locations,
                'form_data': request.POST,
            }
            return render(request, 'accounting/cash_session_open.html', context)

        session = CashRegisterSession.objects.create(
            user=user,
            enterprise=enterprise,
            location_id=location_id if location_id else None,
            opening_balance=opening_balance,
            opened_at=timezone.now(),
            notes=notes or None,
        )

        messages.success(request, f"Session de caisse ouverte avec un solde de {opening_balance} FB.")
        return redirect('accounting:cash_session_detail', pk=session.pk)

    context = {
        'locations': locations,
    }
    return render(request, 'accounting/cash_session_open.html', context)


# Rôle : affiche une session de l'entreprise ; un caissier n'accède qu'à ses propres sessions.
# Liens : route /accounting/cash-sessions/<pk>/, lien dans templates/dashboards/comptable.html et la liste.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier', 'accountant')
def cash_session_detail(request, pk):
    """View cash session details"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    session = get_object_or_404(CashRegisterSession.objects.select_related('user', 'location'), pk=pk)

    if enterprise and session.enterprise and session.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette session.")
        return redirect('accounting:cash_session_list')

    # Cashiers can only see their own sessions
    if user.role == 'cashier' and session.user != user:
        messages.error(request, "Vous n'avez pas accès à cette session.")
        return redirect('accounting:cash_session_list')

    context = {
        'session': session,
    }
    return render(request, 'accounting/cash_session_detail.html', context)


# Rôle : ferme la session et calcule l'écart ; le solde attendu reprend le solde d'ouverture, sans les ventes.
# Liens : route /accounting/cash-sessions/<pk>/close/, liens dans la liste et dans cash_session_detail.html.
# Écrit CashRegisterSession ; rend cash_session_close.html.
@login_required
@role_required('admin', 'owner', 'manager', 'boutique_manager', 'cashier')
def cash_session_close(request, pk):
    """Close a cash register session"""
    user = request.user
    enterprise = getattr(user, 'enterprise', None)

    session = get_object_or_404(CashRegisterSession, pk=pk)

    if enterprise and session.enterprise and session.enterprise != enterprise:
        messages.error(request, "Vous n'avez pas accès à cette session.")
        return redirect('accounting:cash_session_list')

    # Cashiers can only close their own sessions
    if user.role == 'cashier' and session.user != user:
        messages.error(request, "Vous ne pouvez fermer que votre propre session.")
        return redirect('accounting:cash_session_list')

    if session.status == 'closed':
        messages.warning(request, "Cette session est déjà fermée.")
        return redirect('accounting:cash_session_detail', pk=session.pk)

    if request.method == 'POST':
        closing_balance = request.POST.get('closing_balance', '0')
        notes = request.POST.get('notes', '').strip()

        errors = []

        try:
            closing_balance = Decimal(closing_balance)
            if closing_balance < 0:
                errors.append("Le solde de fermeture ne peut pas être négatif.")
        except:
            errors.append("Montant invalide.")

        if errors:
            for error in errors:
                messages.error(request, error)
            context = {
                'session': session,
            }
            return render(request, 'accounting/cash_session_close.html', context)

        # Calculate expected balance (opening + sales - expenses)
        # For now, use opening balance as expected (can be enhanced later)
        expected_balance = session.opening_balance
        difference = closing_balance - expected_balance

        session.closing_balance = closing_balance
        session.expected_balance = expected_balance
        session.difference = difference
        session.closed_at = timezone.now()
        session.status = 'closed'
        if notes:
            session.notes = (session.notes or '') + '\n\n[Fermeture] ' + notes
        session.save()

        if difference == 0:
            messages.success(request, "Session fermée avec succès. La caisse est équilibrée!")
        elif difference > 0:
            messages.success(request, f"Session fermée. Excédent de {difference} FB.")
        else:
            messages.warning(request, f"Session fermée. Déficit de {abs(difference)} FB.")

        return redirect('accounting:cash_session_detail', pk=session.pk)

    context = {
        'session': session,
    }
    return render(request, 'accounting/cash_session_close.html', context)
