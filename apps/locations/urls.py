# Rôle : adresses des emplacements, de leurs types et de leur stock.
# Liens : route vers apps/locations/views.py ; inclus sous locations/ par stock_control/urls.py.
from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.location_create, name='create'),
    # Location types (manageable Emplacement types)
    path('types/', views.type_list, name='type_list'),
    path('types/create/', views.type_create, name='type_create'),
    path('types/<int:pk>/edit/', views.type_edit, name='type_edit'),
    path('types/<int:pk>/delete/', views.type_delete, name='type_delete'),
    path('<int:pk>/', views.location_detail, name='detail'),
    path('<int:pk>/edit/', views.location_edit, name='edit'),
    path('<int:pk>/delete/', views.location_delete, name='delete'),
    path('<int:pk>/stock/', views.location_stock, name='stock'),
]
