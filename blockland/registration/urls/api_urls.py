# registration/urls/api_urls.py
from django.urls import path
from ..views.api_views import parcels_by_owner_api

urlpatterns = [
    path('api/parcels/by-owner/<int:owner_id>/', parcels_by_owner_api, name='parcels_by_owner_api'),
]