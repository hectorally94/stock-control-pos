# Rôle : adresses de connexion de l'API : login, refresh, logout, me et test du jeton JWT.
# Liens : route vers api/v1/auth/views.py et TokenRefreshView ; inclus sous auth/ par api/v1/urls.py.
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    logout_view,
    current_user_view,
    test_token_view
)

urlpatterns = [
    # JWT Authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    path('me/', current_user_view, name='current_user'),
    
    # Test endpoint
    path('test/', test_token_view, name='test_token'),
]

