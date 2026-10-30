# Rôle : adresses des quatre tableaux de bord par rôle : patron, gérant, caisse et comptable.
# Liens : route vers apps/core/dashboard_views.py ; inclus sous dashboard/ par stock_control/urls.py.
"""Role-specific dashboard routes."""
from django.urls import path

from apps.core import dashboard_views

app_name = 'dashboards'

urlpatterns = [
    path('patron/', dashboard_views.patron_dashboard, name='patron'),
    path('gerant/', dashboard_views.gerant_dashboard, name='gerant'),
    path('caisse/', dashboard_views.caisse_dashboard, name='caisse'),
    path('comptable/', dashboard_views.comptable_dashboard, name='comptable'),
]
