from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, logout as django_logout
from django.shortcuts import redirect
from django.utils import timezone

from apps.accounts.models import User, ActionLog


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer to include user role in token"""
    
    # Rôle : ajoute role, username et email dans le contenu du JWT généré par SimpleJWT.
    # Liens : appelée par SimpleJWT pendant validate() ; lit les champs de User (apps/accounts/models.py).
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['role'] = user.role
        token['username'] = user.username
        token['email'] = user.email
        
        return token
    
    # Rôle : après vérification des identifiants, ajoute un bloc user (id, nom, rôle...) à la réponse des tokens.
    # Liens : appelée par DRF depuis CustomTokenObtainPairView.post() ; route POST /api/v1/auth/login/.
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra user data to response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'full_name': self.user.get_full_name(),
            'role': self.user.role,
            'role_display': self.user.get_role_display(),
        }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view with action logging"""
    serializer_class = CustomTokenObtainPairSerializer
    
    # Rôle : connecte via SimpleJWT ; sur réponse 200, journalise le login (avec IP) et met à jour last_login.
    # Liens : route POST /api/v1/auth/login/ (api/v1/auth/urls.py) ; crée un ActionLog (apps/accounts/models.py).
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Log successful login
        if response.status_code == 200:
            username = request.data.get('username')
            try:
                user = User.objects.get(username=username)
                
                # Get client IP
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                
                # Create action log
                ActionLog.objects.create(
                    user=user,
                    action_type='login',
                    entity_type='user',
                    entity_id=user.id,
                    description=f'Login successful for {username}',
                    ip_address=ip_address
                )
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
            except User.DoesNotExist:
                pass
        
        return response


# Rôle : avec JWT et refresh_token valides, invalide ce token et journalise ; sans JWT, redirige vers login.
# Liens : route /api/v1/auth/logout/ ; {% url 'logout' %} de templates/base.html y mène aussi (nom dupliqué).
# La branche session (django_logout) exige un user sans token, or stock_control/settings.py n'active que le JWT.
@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def logout_view(request):
    """
    Logout endpoint - handles both JWT and session authentication.
    - For JWT: POST with {refresh_token: string} to blacklist token
    - For Session: GET or POST to logout and redirect to login page
    """
    # Check if user is authenticated via session (browser)
    if request.user.is_authenticated and not request.auth:
        # Session-based authentication (browser user)
        # Log the logout
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        ActionLog.objects.create(
            user=request.user,
            action_type='logout',
            entity_type='user',
            entity_id=request.user.id,
            description=f'Logout for {request.user.username}',
            ip_address=ip_address
        )

        # Perform Django logout
        django_logout(request)

        # Redirect to login page
        return redirect('login')

    # JWT-based authentication (API client)
    if not request.user.is_authenticated:
        # Not authenticated at all - redirect to login
        return redirect('login')

    try:
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response(
                {'error': 'Le refresh token est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Blacklist the token
        token = RefreshToken(refresh_token)
        token.blacklist()

        # Log logout
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        ActionLog.objects.create(
            user=request.user,
            action_type='logout',
            entity_type='user',
            entity_id=request.user.id,
            description=f'Logout for {request.user.username}',
            ip_address=ip_address
        )

        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


# Rôle : renvoie le profil complet de l'utilisateur identifié par son JWT, y compris rôle et statuts.
# Liens : route GET /api/v1/auth/me/ (api/v1/auth/urls.py) ; lit User (apps/accounts/models.py).
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user info.
    """
    user = request.user
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.get_full_name(),
        'phone': user.phone,
        'role': user.role,
        'role_display': user.get_role_display(),
        'is_active': user.is_active,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'last_login': user.last_login,
        'created_at': user.created_at,
    })


# Rôle : indique le nom de l'utilisateur reconnu par le token, ou Anonymous si aucun token n'est reconnu.
# Liens : route POST /api/v1/auth/test/ (api/v1/auth/urls.py) ; aucun modèle modifié.
@api_view(['POST'])
@permission_classes([AllowAny])
def test_token_view(request):
    """
    Test endpoint to verify JWT token is working.
    For development only.
    """
    return Response({
        'message': 'JWT authentication is working!',
        'user': request.user.username if request.user.is_authenticated else 'Anonymous'
    })

