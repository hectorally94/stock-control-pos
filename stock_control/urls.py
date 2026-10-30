"""
URL configuration for stock_control project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.core.views import functional_documentation
from apps.core.dashboard_views import home_dashboard

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Public functional guide (linked from the login page)
    path('guide/', functional_documentation, name='functional_documentation'),

    # Home — dispatches each user to their role dashboard
    path('', home_dashboard, name='home'),

    # Role-specific dashboards (Patron / Gérant / Caisse / Comptabilité)
    path('dashboard/', include('apps.core.urls')),

    # Frontend Apps
    path('pos/', include('apps.pos.urls')),
    path('stock/', include('apps.stock.urls')),
    path('reports/', include('apps.reports.urls')),
    path('locations/', include('apps.locations.urls')),
    path('transfers/', include('apps.transfers.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('products/', include('apps.products.urls')),
    path('customers/', include('apps.customers.urls')),
    path('accounting/', include('apps.accounting.urls')),

    # API v1
    path('api/v1/', include('api.v1.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
