# registration/urls/profile_urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from ..views.profile_views import ProfileDetailView, ProfileUpdateView, UserUpdateView, HomeView
from ..views.admin_views import SecuritySettingsView
from ..views.dashboard_views import UserDashboardView

app_name = 'profile'

# Role-based redirect view
@login_required
def dashboard_redirect(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_panel:admin_dashboard')
    return redirect('profile:user_dashboard')

urlpatterns = [
    # Home page
    path('home/', login_required(HomeView.as_view()), name='home'),
    
    # Dashboard
    path('dashboard/', login_required(UserDashboardView.as_view()), name='user_dashboard'),

    # Profile management
    path('profile/', login_required(ProfileDetailView.as_view()), name='profile_detail'),
    path('profile/update/', login_required(ProfileUpdateView.as_view()), name='profile_update'),
    path('profile/account/', login_required(UserUpdateView.as_view()), name='account_update'),
    
    # Security settings
    path('profile/security/', login_required(SecuritySettingsView.as_view()), name='security_settings'),

    # Dynamic redirect based on role
    path('redirect/', dashboard_redirect, name='dashboard_redirect'),
]