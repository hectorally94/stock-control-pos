from django.urls import path
from . import views

app_name = 'transfers'

urlpatterns = [
    path('', views.transfer_list, name='list'),
    path('create/', views.transfer_create, name='create'),
    path('<int:pk>/', views.transfer_detail, name='detail'),
    path('<int:pk>/send/', views.transfer_send, name='send'),
    path('<int:pk>/receive/', views.transfer_receive, name='receive'),
    path('<int:pk>/cancel/', views.transfer_cancel, name='cancel'),
]
