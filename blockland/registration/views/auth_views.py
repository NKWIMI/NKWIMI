# registration/views/auth_views.py

from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
)
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import CreateView, FormView, View
from django.contrib.auth import login as auth_login, get_user_model
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from eth_account import Account  # ✅ Blockchain key generation

from ..forms.auth_forms import (  # ✅ Custom auth forms
    CustomAuthenticationForm,
    UserRegistrationForm,
    EmailVerificationForm,
)

from ..services.file_hash_service import FileHashService  # ✅ Blockchain file service
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.http import HttpResponseForbidden

User = get_user_model()


# ------------------------
# Password Management Views
# ------------------------

class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("auth:password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("auth:password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"


class CustomPasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("auth:password_change_done")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Change Password"
        return context


# ------------------------
# Registration & Login Views
# ------------------------

class UserRegistrationView(UserPassesTestMixin, CreateView):
    form_class = UserRegistrationForm    
    template_name = "registration/register_user.html"
    
    def test_func(self):
        # Only allow admin users to access this view
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.is_superuser)
    
    def handle_no_permission(self):
        # Redirect non-admin users to home page with error message
        messages.error(self.request, "Only administrators can create user accounts.")
        return redirect('home')
    
    def dispatch(self, request, *args, **kwargs):
        # Handle the case when user is not authenticated
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect('auth:login')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Only proceed if user is admin
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            return HttpResponseForbidden("Only administrators can create user accounts.")
            
        response = super().form_valid(form)
        user = form.instance

        # Create or update profile
        if hasattr(user, "profile"):
            profile = user.profile
            profile.phone_number = form.cleaned_data.get("phone_number", "")
            profile.address_text = form.cleaned_data.get("address_text", "")

            # Handle file upload + blockchain hash
            if "identity_document" in self.request.FILES:
                file_service = FileHashService()
                profile.identity_document = self.request.FILES["identity_document"]
                profile.identity_document_hash = file_service.add_file(
                    self.request.FILES["identity_document"]
                )

            # Generate blockchain credentials
            acct = Account.create()
            profile.blockchain_address = acct.address
            profile.encrypted_private_key = acct.key.hex()
            profile.save()

        messages.success(
            self.request, "🎉 User account created successfully!"
        )
        return redirect('admin_panel:admin_manage_users')  # Redirect to user management


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return reverse_lazy("admin_panel:admin_dashboard")
        return reverse_lazy("profile:user_dashboard")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("home")


# ------------------------
# Email Verification Views
# ------------------------

class VerifyEmailView(LoginRequiredMixin, FormView):
    template_name = "verify_email_form.html"
    form_class = EmailVerificationForm
    success_url = reverse_lazy("auth:verify_email_done")

    def form_valid(self, form):
        user = self.request.user
        self.send_verification_email(user)
        messages.success(
            self.request, "📧 Verification email sent. Please check your inbox."
        )
        return super().form_valid(form)

    def send_verification_email(self, user):
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = self.request.build_absolute_uri(
            reverse("verify_email_confirm", kwargs={"uidb64": uid, "token": token})
        )
        subject = "Verify your email address"
        message = render_to_string(
            "verify_email_message.txt",
            {
                "user": user,
                "verification_url": verification_url,
            },
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )


class VerifyEmailConfirmView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            # ✅ If `email_verified` is now directly on User
            user.email_verified = True
            user.save()

            messages.success(request, "✅ Your email has been verified!")
            return redirect("profile")
        else:
            messages.error(
                request, "⚠️ The verification link was invalid or has expired."
            )
            return redirect("verify_email")