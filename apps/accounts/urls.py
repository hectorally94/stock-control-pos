# Rôle : adresses de gestion des utilisateurs : liste, création, détail, modification, activation.
# Liens : route vers apps/accounts/views.py ; inclus sous accounts/ par stock_control/urls.py.
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
]
