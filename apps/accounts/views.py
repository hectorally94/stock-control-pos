from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Q

from .models import User
from apps.locations.models import Location


# Rôle : fabrique un décorateur qui réserve une vue web aux rôles indiqués.
# Liens : utilisé par les vues de ce fichier ; d'autres apps ont leur propre copie (ex. apps/products/views.py).
def role_required(*roles):
    """Decorator to check if user has required role"""
    # Rôle : reçoit la vue à protéger et la remplace par la fonction wrapper.
    # Liens : usage local, appliqué par la syntaxe @role_required(...) au chargement du module.
    def decorator(view_func):
        # Rôle : envoie l'anonyme vers « login » et le rôle refusé vers « home » avec un message d'erreur.
        # Liens : exécutée à chaque requête ; « home » est home_dashboard (apps/core/dashboard_views.py).
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                return redirect('home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Rôle : liste les utilisateurs de l'entreprise avec filtres rôle, emplacement, statut et recherche.
# Liens : route accounts:user_list (apps/accounts/urls.py), lien du menu templates/base.html.
# Rend apps/accounts/templates/accounts/user_list.html ; lit User et Location.
@login_required
@role_required('admin', 'owner', 'manager')
def user_list(request):
    """List all users for the enterprise"""
    user = request.user

    if not hasattr(user, 'enterprise') or not user.enterprise:
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('home')

    # Get users for this enterprise
    users = User.objects.filter(
        enterprise=user.enterprise
    ).select_related('location').order_by('role', 'username')

    # Filter by role
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)

    # Filter by location
    location_filter = request.GET.get('location')
    if location_filter:
        users = users.filter(location_id=location_filter)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )

    # Get locations for filter
    locations = Location.objects.filter(
        enterprise=user.enterprise, is_active=True
    ).order_by('name')

    # Stats
    total_users = users.count()
    active_users = users.filter(is_active=True).count()

    context = {
        'users': users,
        'locations': locations,
        'role_choices': User.ROLE_CHOICES,
        'selected_role': role_filter,
        'selected_location': location_filter,
        'selected_status': status_filter,
        'search': search or '',
        'total_users': total_users,
        'active_users': active_users,
    }
    return render(request, 'accounts/user_list.html', context)


# Rôle : crée un utilisateur après validation ; un manager ne peut pas attribuer admin, owner ou manager.
# Liens : route accounts:user_create ; rend apps/accounts/templates/accounts/user_create.html.
# Crée un User dans l'entreprise de l'auteur ; mot de passe haché par make_password.
@login_required
@role_required('admin', 'owner', 'manager')
def user_create(request):
    """Create a new user"""
    user = request.user

    if not hasattr(user, 'enterprise') or not user.enterprise:
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('accounts:user_list')

    # Get locations for dropdown
    locations = Location.objects.filter(
        enterprise=user.enterprise, is_active=True
    ).order_by('location_type', 'name')

    # Determine which roles the current user can create
    # Admin/Owner can create all roles, Manager cannot create admin/owner
    if user.role in ('admin', 'owner'):
        available_roles = User.ROLE_CHOICES
    else:
        # Manager can only create lower-level roles
        available_roles = [
            r for r in User.ROLE_CHOICES
            if r[0] not in ('admin', 'owner', 'manager')
        ]

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role')
        location_id = request.POST.get('location')
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()

        # Validate
        errors = []

        if not username:
            errors.append("Le nom d'utilisateur est requis.")
        elif User.objects.filter(username=username).exists():
            errors.append("Ce nom d'utilisateur existe déjà.")

        if not email:
            errors.append("L'email est requis.")
        elif User.objects.filter(email=email).exists():
            errors.append("Cet email est déjà utilisé.")

        if not password:
            errors.append("Le mot de passe est requis.")
        elif len(password) < 6:
            errors.append("Le mot de passe doit contenir au moins 6 caractères.")
        elif password != password_confirm:
            errors.append("Les mots de passe ne correspondent pas.")

        if not role:
            errors.append("Le rôle est requis.")
        elif role not in [r[0] for r in available_roles]:
            errors.append("Rôle non autorisé.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create user
            location = None
            if location_id:
                try:
                    location = Location.objects.get(pk=location_id, enterprise=user.enterprise)
                except Location.DoesNotExist:
                    pass

            new_user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role=role,
                enterprise=user.enterprise,
                location=location,
                password=make_password(password),
                is_active=True,
            )

            messages.success(request, f"Utilisateur {new_user.username} créé avec succès.")
            return redirect('accounts:user_list')

    context = {
        'locations': locations,
        'role_choices': available_roles,
    }
    return render(request, 'accounts/user_create.html', context)


# Rôle : affiche la fiche d'un utilisateur, seulement s'il est de la même entreprise.
# Liens : route accounts:user_detail ; rend apps/accounts/templates/accounts/user_detail.html.
@login_required
@role_required('admin', 'owner', 'manager')
def user_detail(request, pk):
    """View user details"""
    user = request.user
    target_user = get_object_or_404(User, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != target_user.enterprise:
        messages.error(request, "Vous n'avez pas accès à cet utilisateur.")
        return redirect('accounts:user_list')

    context = {
        'target_user': target_user,
    }
    return render(request, 'accounts/user_detail.html', context)


# Rôle : modifie un autre utilisateur ; refuse sa propre fiche et les rôles plus élevés dans la hiérarchie.
# Liens : route accounts:user_edit ; rend apps/accounts/templates/accounts/user_edit.html ; écrit sur User.
@login_required
@role_required('admin', 'owner', 'manager')
def user_edit(request, pk):
    """Edit a user"""
    user = request.user
    target_user = get_object_or_404(User, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != target_user.enterprise:
        messages.error(request, "Vous n'avez pas accès à cet utilisateur.")
        return redirect('accounts:user_list')

    # Cannot edit yourself here (use profile instead)
    if target_user.pk == user.pk:
        messages.warning(request, "Utilisez les paramètres du profil pour modifier vos propres informations.")
        return redirect('accounts:user_list')

    # Check role hierarchy - cannot edit someone with higher role
    role_hierarchy = ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager', 'cashier', 'accountant']
    user_rank = role_hierarchy.index(user.role) if user.role in role_hierarchy else 999
    target_rank = role_hierarchy.index(target_user.role) if target_user.role in role_hierarchy else 999

    if target_rank < user_rank:
        messages.error(request, "Vous ne pouvez pas modifier un utilisateur avec un rôle supérieur.")
        return redirect('accounts:user_list')

    # Get locations for dropdown
    locations = Location.objects.filter(
        enterprise=user.enterprise, is_active=True
    ).order_by('location_type', 'name')

    # Determine which roles the current user can assign
    if user.role in ('admin', 'owner'):
        available_roles = User.ROLE_CHOICES
    else:
        available_roles = [
            r for r in User.ROLE_CHOICES
            if r[0] not in ('admin', 'owner', 'manager')
        ]

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role')
        location_id = request.POST.get('location')
        new_password = request.POST.get('new_password', '').strip()

        # Validate
        errors = []

        if not email:
            errors.append("L'email est requis.")
        elif User.objects.filter(email=email).exclude(pk=target_user.pk).exists():
            errors.append("Cet email est déjà utilisé.")

        if not role:
            errors.append("Le rôle est requis.")
        elif role not in [r[0] for r in available_roles]:
            errors.append("Rôle non autorisé.")

        if new_password and len(new_password) < 6:
            errors.append("Le mot de passe doit contenir au moins 6 caractères.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Update user
            target_user.email = email
            target_user.first_name = first_name
            target_user.last_name = last_name
            target_user.phone = phone
            target_user.role = role

            if location_id:
                try:
                    target_user.location = Location.objects.get(pk=location_id, enterprise=user.enterprise)
                except Location.DoesNotExist:
                    target_user.location = None
            else:
                target_user.location = None

            if new_password:
                target_user.password = make_password(new_password)

            target_user.save()

            messages.success(request, f"Utilisateur {target_user.username} modifié avec succès.")
            return redirect('accounts:user_list')

    context = {
        'target_user': target_user,
        'locations': locations,
        'role_choices': available_roles,
    }
    return render(request, 'accounts/user_edit.html', context)


# Rôle : active ou désactive un compte (is_active) sur POST ; refuse soi-même et les rôles plus élevés.
# Liens : route accounts:user_toggle_active ; formulaires des templates user_list.html et user_detail.html.
@login_required
@role_required('admin', 'owner', 'manager')
def user_toggle_active(request, pk):
    """Toggle user active status"""
    user = request.user
    target_user = get_object_or_404(User, pk=pk)

    # Check access
    if hasattr(user, 'enterprise') and user.enterprise != target_user.enterprise:
        messages.error(request, "Vous n'avez pas accès à cet utilisateur.")
        return redirect('accounts:user_list')

    # Cannot deactivate yourself
    if target_user.pk == user.pk:
        messages.error(request, "Vous ne pouvez pas vous désactiver vous-même.")
        return redirect('accounts:user_list')

    # Check role hierarchy
    role_hierarchy = ['admin', 'owner', 'manager', 'warehouse_manager', 'boutique_manager', 'stock_manager', 'cashier', 'accountant']
    user_rank = role_hierarchy.index(user.role) if user.role in role_hierarchy else 999
    target_rank = role_hierarchy.index(target_user.role) if target_user.role in role_hierarchy else 999

    if target_rank < user_rank:
        messages.error(request, "Vous ne pouvez pas modifier un utilisateur avec un rôle supérieur.")
        return redirect('accounts:user_list')

    if request.method == 'POST':
        target_user.is_active = not target_user.is_active
        target_user.save()

        status = "activé" if target_user.is_active else "désactivé"
        messages.success(request, f"Utilisateur {target_user.username} {status}.")

    return redirect('accounts:user_list')
