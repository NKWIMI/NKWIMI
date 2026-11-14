# registration/urls/__init__.py
from django.urls import path, include

app_name = 'registration'  # ← ADD THIS LINE

# Import submodules
from registration.urls.core_urls import urlpatterns as core_urls
from registration.urls.auth_urls import urlpatterns as auth_urls
from registration.urls.parcel_urls import urlpatterns as parcel_urls
from registration.urls.profile_urls import urlpatterns as profile_urls
from registration.urls.transfer_urls import urlpatterns as transfer_urls
from registration.urls.blockchain_urls import urlpatterns as blockchain_urls
from registration.urls.transaction_urls import urlpatterns as transaction_urls
from registration.urls.blockchain_info_urls import urlpatterns as blockchain_info_urls
from registration.urls.admin_urls import urlpatterns as admin_urls
urlpatterns = [
    # Core pages (e.g., home, about)
    path('', include((core_urls, 'core'), namespace='core')),

    # Admin pages
    path('admin/', include((admin_urls, 'admin_panel'), namespace='admin_panel')),

    # Authentication (login, register, logout, password reset)
    path('', include((auth_urls, 'auth'), namespace='auth')),

    # Profile and dashboards
    path('profile/', include((profile_urls, 'profile'), namespace='profile')),

    # Parcel-related pages
    path('parcel/', include((parcel_urls, 'parcel'), namespace='parcel')),

    # Transfer-related pages
    path('transfer/', include((transfer_urls, 'transfer'), namespace='transfer')),

    # Blockchain-related pages
    path('blockchain/', include((blockchain_urls, 'blockchain'), namespace='blockchain')),

    # Transaction pages
    path('transactions/', include((transaction_urls, 'transactions'), namespace='transactions')),

    # Blockchain info pages
    path('info/', include((blockchain_info_urls, 'info'), namespace='info')),
]