# blockland/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.storage import staticfiles_storage

from blockland.views import handler400, handler403, handler404, handler500
from registration.views import BlockExplorerView
from registration.views.admin_views import AdminTransferDebugView
from registration.views.core_views import HomeView, AIDocumentationView, APIDocumentationView

urlpatterns = [
    path('register-user/', RedirectView.as_view(url='/accounts/register/'), name='register_user'),
    path('django-admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('admin/', include('registration.urls.admin_urls', namespace='admin_panel')),
    path('accounts/', include('registration.urls.auth_urls', namespace='auth')),
    path('accounts/profile/', include('registration.urls.profile_urls', namespace='profile')),
    path('transaction/', include('registration.urls.transaction_urls', namespace='transaction')),
    path('transfer/', include('registration.urls.transfer_urls', namespace='transfer')),  # This is correct

    path('info/', include('registration.urls.blockchain_info_urls', namespace='info')),
    path('parcel/', include('registration.urls.parcel_urls', namespace='parcel')),
    path('blockchain/', include('registration.urls.blockchain_urls', namespace='blockchain')),
    path('docs/', TemplateView.as_view(template_name="core/docs.html"), name="docs"),
    path('ai-doc/', AIDocumentationView.as_view(), name="ai-doc"),
    path('api-doc/', APIDocumentationView.as_view(), name="api-doc"),
    path('', include('registration.urls.api_urls')),
    path('blockchain/explorer/', BlockExplorerView.as_view(), name='blockchain-explorer'),
    path('favicon.ico', RedirectView.as_view(
        url=staticfiles_storage.url('images/favicon.ico')
    ), name='favicon'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = handler400
handler403 = handler403
handler404 = handler404
handler500 = handler500