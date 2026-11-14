# registration/urls/parcel_urls.py
from django.urls import path
from ..views.parcel_views import (
    ParcelListView, ParcelDetailView, ParcelCreateView,
    ParcelUpdateView, ParcelDeleteView, FreezeParcelView,
    ParcelMetadataView, ParcelPrintView
)

# defines the app namespace
app_name = 'parcel'

urlpatterns = [
    path('parcels/', ParcelListView.as_view(), name='parcel_list'),
    path('parcels/create/', ParcelCreateView.as_view(), name='parcel_create'),
    path('parcels/register/', ParcelCreateView.as_view(), name='parcel_register'),  # Use existing view
    path('parcels/<int:pk>/', ParcelDetailView.as_view(), name='parcel_detail'),
    path('parcels/<int:pk>/update/', ParcelUpdateView.as_view(), name='parcel_update'),
    path('parcels/<int:pk>/delete/', ParcelDeleteView.as_view(), name='parcel_delete'),
    path('parcels/<int:pk>/freeze/', FreezeParcelView.as_view(), name='parcel_freeze'),
    path('parcels/<int:pk>/metadata/', ParcelMetadataView.as_view(), name='parcel_metadata'),
    path('parcels/<int:pk>/print/', ParcelPrintView.as_view(), name='parcel_print'),
]