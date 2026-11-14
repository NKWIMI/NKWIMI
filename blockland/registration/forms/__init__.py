# registration/forms/__init__.py
from .auth_forms import LoginForm, RegisterForm, CustomPasswordResetForm
from .profile_forms import UserForm, UserUpdateForm
from .contact_form import ContactForm
from .transfer_forms import InitiateTransferForm, AcceptTransferForm, CancelTransferForm, RejectTransferForm

# DO NOT import parcel forms here to avoid circular imports
# from .parcel_forms import ParcelTransferForm, ParcelRegistrationForm

__all__ = [
    'LoginForm',
    'RegisterForm', 
    'CustomPasswordResetForm',
    'UserForm',
    'UserUpdateForm',
    'ContactForm',
    'InitiateTransferForm',
    'AcceptTransferForm',
    'CancelTransferForm',
    'RejectTransferForm',
    # Remove these to avoid circular imports:
    # 'ParcelTransferForm',
    # 'ParcelRegistrationForm',
]