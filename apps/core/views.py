"""
Core views.

The role-aware home dashboard now lives in `apps.core.dashboard_views`
(`home_dashboard` dispatches each user to their Patron / Gérant / Caisse /
Comptabilité dashboard). This module keeps the public functional guide.
"""
import os
from django.conf import settings
from django.http import HttpResponse, Http404


# Rôle : renvoie le guide HTML tel quel, sans connexion ni moteur de templates ; 404 si le fichier manque.
# Liens : route /guide/ de stock_control/urls.py, lien dans templates/login.html ;
# lit docs/functional_documentation.html.
def functional_documentation(request):
    """Serve the standalone functional guide.

    Public on purpose (no login required) so it can be opened from the login
    page. The HTML is self-contained and returned as-is rather than through the
    template engine (it contains JS braces that must not be parsed by Django).
    """
    path = os.path.join(settings.BASE_DIR, 'docs', 'functional_documentation.html')
    try:
        with open(path, encoding='utf-8') as f:
            return HttpResponse(f.read())
    except FileNotFoundError:
        raise Http404("Documentation introuvable.")
