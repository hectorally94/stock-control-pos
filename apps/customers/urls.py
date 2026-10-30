from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Customer CRUD
    path('', views.customer_list, name='customer_list'),
    path('create/', views.customer_create, name='customer_create'),
    path('<int:pk>/', views.customer_detail, name='customer_detail'),
    path('<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('<int:pk>/toggle/', views.customer_toggle, name='customer_toggle'),

    # Credits & Payments
    path('credits/', views.credit_list, name='credit_list'),
    path('credits/<int:credit_id>/pay/', views.record_payment, name='record_payment'),
    path('<int:customer_id>/payments/', views.payment_history, name='payment_history'),
]
