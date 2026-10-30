# Rôle : adresses de la caisse : page caisse, tableau de bord, ventes, recherche, créations et reçu PDF.
# Liens : route vers apps/pos/views_frontend.py ; inclus sous pos/ par stock_control/urls.py.
from django.urls import path
from apps.pos import views_frontend

app_name = 'pos'

urlpatterns = [
    path('', views_frontend.cashier_view, name='cashier'),
    path('dashboard/', views_frontend.sales_dashboard, name='dashboard'),
    path('sales/', views_frontend.sales_list, name='sales_list'),
    path('search/', views_frontend.search_products, name='search_products'),
    path('create-sale/', views_frontend.create_sale_view, name='create_sale'),
    path('create-customer/', views_frontend.create_customer_view, name='create_customer'),
    path('sales/<int:sale_id>/receipt/', views_frontend.sale_receipt_pdf, name='sale_receipt'),
]

