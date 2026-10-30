# Rôle : adresses des catégories de dépenses, des dépenses et des sessions de caisse.
# Liens : route vers apps/accounting/views.py ; inclus sous accounting/ par stock_control/urls.py.
from django.urls import path
from . import views

app_name = 'accounting'

urlpatterns = [
    # Expense Categories
    path('expense-categories/', views.expense_category_list, name='expense_category_list'),
    path('expense-categories/create/', views.expense_category_create, name='expense_category_create'),
    path('expense-categories/<int:pk>/edit/', views.expense_category_edit, name='expense_category_edit'),

    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/create/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/', views.expense_detail, name='expense_detail'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Cash Register Sessions
    path('cash-sessions/', views.cash_session_list, name='cash_session_list'),
    path('cash-sessions/open/', views.cash_session_open, name='cash_session_open'),
    path('cash-sessions/<int:pk>/', views.cash_session_detail, name='cash_session_detail'),
    path('cash-sessions/<int:pk>/close/', views.cash_session_close, name='cash_session_close'),
]
