# registration/api/urls.py
from django.urls import path
from .views import (  # Changed from api_views to views
    user_list, 
    user_detail,
    parcel_list,
    parcel_detail
)

app_name = 'api'

urlpatterns = [
    path('users/', user_list, name='user-list'),
    path('users/<int:user_id>/', user_detail, name='user-detail'),
    path('parcels/', parcel_list, name='parcel-list'), 
    path('parcels/<int:parcel_id>/', parcel_detail, name='parcel-detail'),
    
    
]