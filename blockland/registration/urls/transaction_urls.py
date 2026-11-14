# registration/urls/transaction_urls.py
from django.urls import path
from ..views.transaction_views import TransactionListView

app_name = 'transaction'

urlpatterns = [
    path('', TransactionListView.as_view(), name='transaction_list'),
    path('history/', TransactionListView.as_view(), name='transaction_history'),
]