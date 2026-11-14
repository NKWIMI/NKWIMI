from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateView
from registration.views import auth_views as auth_views_custom

app_name = 'auth_api'  # Optional, for namespacing

urlpatterns = [
    # ------------------------
    # Authentication
    # ------------------------
    path('register/', auth_views_custom.UserRegistrationView.as_view(), name='register'),
    path('login/', auth_views_custom.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views_custom.CustomLogoutView.as_view(), name='logout'),

    # ------------------------
    # Password Management
    # ------------------------
    path('password/', include([
        path('change/', login_required(auth_views_custom.CustomPasswordChangeView.as_view()), name='password_change'),
        path('change/done/', login_required(auth_views.PasswordChangeDoneView.as_view(
            template_name='auth/password_change_done.html'
        )), name='password_change_done'),

        path('reset/', include([
            path('', auth_views_custom.CustomPasswordResetView.as_view(), name='password_reset'),
            path('done/', auth_views_custom.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
            path('confirm/<uidb64>/<token>/', auth_views_custom.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
            path('complete/', auth_views_custom.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
        ])),
    ])),

    # ------------------------
    # Email Verification
    # ------------------------
    path('verify/', include([
        path('email/', auth_views_custom.VerifyEmailView.as_view(), name='verify_email'),
        path('email/done/', TemplateView.as_view(template_name='auth/verify_email_done.html'), name='verify_email_done'),
        path('email/<uidb64>/<token>/', auth_views_custom.VerifyEmailConfirmView.as_view(), name='verify_email_confirm'),
    ])),
]
