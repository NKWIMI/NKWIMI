from django.urls import path
from django.contrib.auth.views import PasswordChangeDoneView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from ..views.auth_views import (
    UserRegistrationView,  # This is the correct view class
    CustomLoginView,
    CustomLogoutView,
    CustomPasswordChangeView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
    VerifyEmailView,
    VerifyEmailConfirmView
)

app_name = 'auth'

urlpatterns = [
    # User registration - use UserRegistrationView (the one that exists)
    path("register/", staff_member_required(UserRegistrationView.as_view()), name="user_create"),
    
    # Authentication
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    
    # Password management
    path("password/change/", CustomPasswordChangeView.as_view(), name="password_change"),
    path("password/change/done/", PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("password/reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path("password/reset/done/", CustomPasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/confirm/<uidb64>/<token>/", CustomPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", CustomPasswordResetCompleteView.as_view(), name="password_reset_complete"),
    
    # Email verification
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("verify-email/confirm/<uidb64>/<token>/", VerifyEmailConfirmView.as_view(), name="verify_email_confirm"),
]