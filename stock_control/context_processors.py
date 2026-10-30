from django.conf import settings


# Rôle : ajoute la variable DEBUG au contexte de chaque template.
# Liens : déclarée dans TEMPLATES de stock_control/settings.py ; aucun template actuel ne lit cette variable.
def debug_context(request):
    """Add DEBUG setting to template context for development helpers."""
    return {
        'DEBUG': settings.DEBUG,
    }
