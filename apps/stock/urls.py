from django.urls import path
from apps.stock import views_frontend

app_name = 'stock'

urlpatterns = [
    path('', views_frontend.dashboard_view, name='dashboard'),
    path('entry/', views_frontend.entry_view, name='entry'),
    path('in-stock/', views_frontend.in_stock_view, name='in_stock'),
    path('low-stock/', views_frontend.low_stock_view, name='low_stock'),
    path('out-of-stock/', views_frontend.out_of_stock_view, name='out_of_stock'),
    path('movements/', views_frontend.movements_view, name='movements'),
]

