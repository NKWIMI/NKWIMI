# registration/urls/core_urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from ..views.core_views import (
    HomeView,
    AboutView,
    ContactView,
    DocumentationView,
    AIDocumentationView,
    APIDocumentationView
)

app_name = 'core'

urlpatterns = [
    # REMOVE THIS LINE: path('', HomeView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('docs/', login_required(DocumentationView.as_view()), name='docs'),
    path('ai-doc/', login_required(AIDocumentationView.as_view()), name='ai_doc'),
    path('api-doc/', login_required(APIDocumentationView.as_view()), name='api_doc'),
]