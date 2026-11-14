from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.conf import settings
from eth_account import Account
from registration.services.file_hash_service import FileHashService
from ..models import User


class UserRegistrationForm(forms.ModelForm):
    """
    Custom registration form for our custom User model
    """
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Create a strong password'
        })
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Repeat your password'
        }),
        help_text="Enter the same password as above, for verification."
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'your@email.com'
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '+1234567890'
        }),
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Enter a valid phone number (e.g. +1234567890)"
            )
        ]
    )

    address_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-lg',
            'rows': 3,
            'placeholder': 'Your full address...'
        })
    )

    identity_document = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control form-control-lg',
            'accept': '.pdf,.jpg,.jpeg,.png'
        }),
        help_text="Upload a clear scan of your government-issued ID"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'address_text', 'identity_document']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Choose a username'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")
        return email

    def clean_identity_document(self):
        document = self.cleaned_data.get('identity_document')
        if document.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError("Document size must be less than 10MB")
        return document

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        user.address_text = self.cleaned_data['address_text']
        user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()

            # Process ID document
            file_service = FileHashService(
                use_ipfs=bool(settings.IPFS_API_KEY and settings.IPFS_API_SECRET)
            )
            
            # Handle identity document
            identity_document = self.cleaned_data['identity_document']
            if identity_document:
                user.identity_document = identity_document
                user.identity_document_hash = file_service.add_file(identity_document)

            # Generate blockchain credentials if not already set
            if not user.blockchain_address:
                acct = Account.create()
                user.blockchain_address = acct.address
                user.encrypted_private_key = acct.key.hex()

            user.save()

        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Allow email or username login
            if '@' in username:
                try:
                    user = User.objects.get(email__iexact=username)
                    username = user.username
                except User.DoesNotExist:
                    raise ValidationError(
                        "No account found with that email address"
                    )

            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )

            if self.user_cache is None:
                raise ValidationError(
                    "Please enter a correct username/email and password"
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class EmailVerificationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError("No account exists with this email address.")
        return email


# --------------------------
# Aliases for backward compatibility
# --------------------------
class LoginForm(CustomAuthenticationForm):
    """Alias for login form (uses CustomAuthenticationForm)"""
    pass

class RegisterForm(UserRegistrationForm):
    """Alias for registration form (uses UserRegistrationForm)"""
    pass

class CustomPasswordResetForm(EmailVerificationForm):
    """Temporary alias until you implement full reset"""
    pass