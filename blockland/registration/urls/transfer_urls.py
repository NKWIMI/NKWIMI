from django.urls import path
from ..views.transfer_views import (
    TransferListView,
    TransferCreateView,
    TransferDetailView,
    TransferAcceptView,
    TransferCancelView,
    TransferRejectView,
    TransferHistoryView,
    TransferPrintView
)

app_name = 'transfer'

urlpatterns = [
    path('', TransferListView.as_view(), name='transfer_list'),
    path('create/', TransferCreateView.as_view(), name='transfer_create'),
    path('<int:pk>/', TransferDetailView.as_view(), name='transfer_detail'),  # Correct pattern
    path('<int:pk>/accept/', TransferAcceptView.as_view(), name='transfer_accept'),
    path('<int:pk>/cancel/', TransferCancelView.as_view(), name='transfer_cancel'),
    path('<int:pk>/reject/', TransferRejectView.as_view(), name='transfer_reject'),
    path('history/', TransferHistoryView.as_view(), name='transfer_history'),
    path('<int:pk>/print/', TransferPrintView.as_view(), name='transfer_print'),
]