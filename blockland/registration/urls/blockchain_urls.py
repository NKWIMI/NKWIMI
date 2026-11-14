# registration/urls/blockchain_urls.py
from django.urls import path
from ..views.blockchain_views import (
    BlockExplorerView,
    BlockDetailView,
    TransactionListView,
    BlockchainSearchView,
    AddressDetailView,
    BlockchainSyncView,
    BlockchainStatusView
)

app_name = 'blockchain'

urlpatterns = [
    #path('explorer/', BlockExplorerView.as_view(), name='block_explorer'),
    path('block/<int:height>/', BlockDetailView.as_view(), name='block_detail'),
    path('block/<str:hash>/', BlockDetailView.as_view(), name='block_detail_hash'),
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('search/', BlockchainSearchView.as_view(), name='blockchain_search'),
    path('address/<str:address>/', AddressDetailView.as_view(), name='address_detail'),
    path('sync/', BlockchainSyncView.as_view(), name='blockchain_sync'),
    path('status/', BlockchainStatusView.as_view(), name='blockchain_status'),
]