# registration/views/__init__.py
from importlib import import_module
from django.utils.module_loading import import_string

# Core view imports
from .contact_views import ContactView
from .error_views import (
    bad_request_view, permission_denied_view,
    page_not_found_view, server_error_view
)
from .auth_views import (
    CustomPasswordResetView, CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView, CustomPasswordResetCompleteView,
    CustomPasswordChangeView, UserRegistrationView,
    CustomLoginView, CustomLogoutView,
    VerifyEmailView, VerifyEmailConfirmView
)
from .core_views import HomeView
from .profile_views import (
    ProfileDetailView, ProfileUpdateView, UserUpdateView
)
from .parcel_views import (
    ParcelListView, ParcelDetailView, RegisterParcelView,
    ParcelUpdateView, FreezeParcelView, ParcelMetadataView
)
from .transfer_views import (
    TransferListView, TransferCreateView, TransferDetailView,
    TransferAcceptView, TransferCancelView, TransferHistoryView,
    TransferRejectView
)
from .admin_views import (
    AdminBaseView, AdminDashboardView, AdminManageUsersView,
    AdminUserDetailView, AdminVerifyUserView, AdminViewTransactionsView,
    AdminManageParcelsView, AdminViewLogsView, AdminGenerateReportsView,
    SecuritySettingsView
)
from .dashboard_views import UserDashboardView
from .account import AccountOverview, AccountSettingsView
from .blockchain_views import (
    BlockExplorerView,
    TransactionListView as BlockchainTransactionListView
)
from .transaction_views import TransactionListView,AdminViewTransactionsView

# Export all views
__all__ = [
    # Error views
    'ContactView',
    'bad_request_view', 'permission_denied_view',
    'page_not_found_view', 'server_error_view',

    # Auth views
    'CustomPasswordResetView', 'CustomPasswordResetDoneView',
    'CustomPasswordResetConfirmView', 'CustomPasswordResetCompleteView',
    'CustomPasswordChangeView', 'UserRegistrationView',
    'CustomLoginView', 'CustomLogoutView',
    'VerifyEmailView', 'VerifyEmailConfirmView',

    # Core views
    'HomeView', 'AdminDashboardView',

    # Profile views
    'ProfileDetailView', 'ProfileUpdateView', 'UserUpdateView',

    # Parcel views
    'ParcelListView', 'ParcelDetailView', 'RegisterParcelView',
    'ParcelUpdateView', 'FreezeParcelView', 'ParcelMetadataView',

    # Transfer views
    'TransferListView', 'TransferCreateView', 'TransferDetailView',
    'TransferAcceptView', 'TransferCancelView', 'TransferHistoryView',
    'TransferRejectView',

    # Admin views
    'AdminBaseView', 'AdminDashboardView', 'AdminManageUsersView',
    'AdminUserDetailView', 'AdminVerifyUserView', 'AdminViewTransactionsView',
    'AdminManageParcelsView', 'AdminViewLogsView', 'AdminGenerateReportsView',
    'SecuritySettingsView',

    # Transaction views
    'TransactionListView', 'BlockchainTransactionListView',

    # Account and Dashboard views
    'AccountOverview', 'AccountSettingsView', 'UserDashboardView',

    # Blockchain views
    'BlockExplorerView'
]

# Clean up the namespace
del import_module, import_string
