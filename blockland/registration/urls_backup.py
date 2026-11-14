# registration/urls.py

from django.urls import path, include

app_name = "registration"

urlpatterns = [
    # Authentication URLs
    path("auth/", include(("registration.urls.auth_urls", "auth"), namespace="auth")),

    # Profile-related URLs
    #path("profile/", include(("registration.urls.profile_urls", "profile"), namespace="profile")),
    path("profile/", include(("registration.profile_urls", "profile"), namespace="profile")),

    # Parcel management URLs
    path("parcel/", include(("registration.urls.parcel_urls", "parcel"), namespace="parcel")),

    # Transfer-related URLs
    path("transfer/", include(("registration.urls.transfer_urls", "transfer"), namespace="transfer")),

    # Admin-specific URLs
    path("admin/dashboard/", include(("registration.urls.admin_urls", "admin"), namespace="admin")),

    # Blockchain-related URLs
    path("blockchain/", include(("registration.urls.blockchain_urls", "blockchain"), namespace="blockchain")),

    # Dashboard URLs
    path("dashboard/", include(("registration.urls.dashboard_urls", "dashboard"), namespace="dashboard")),

    # Transaction URLs
    path("transactions/", include(("registration.urls.transaction_urls", "transactions"), namespace="transactions")),

    # Blockchain info URLs (⚡ this is the one causing your error)
    path("info/", include(("registration.urls.blockchain_info_urls", "info"), namespace="info")),

    # API URLs
    path("api/", include(("registration.api.urls", "api"), namespace="api")),
]
