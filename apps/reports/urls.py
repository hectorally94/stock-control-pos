# Rôle : adresses du tableau de bord des rapports et des quatre exports Excel.
# Liens : route vers apps/reports/views.py ; inclus sous reports/ par stock_control/urls.py.
from django.urls import path
from apps.reports import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    
    # Excel exports
    path('export/sales/', views.export_sales_report, name='export_sales'),
    path('export/inventory/', views.export_inventory_report, name='export_inventory'),
    path('export/expenses/', views.export_expense_report, name='export_expenses'),
    path('export/customers/', views.export_customer_report, name='export_customers'),
]

