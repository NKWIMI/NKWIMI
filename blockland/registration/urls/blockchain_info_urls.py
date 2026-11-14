# registration/urls/blockchain_info_urls.py
from django.urls import path
from ..views.info_views import BlockchainInfoView, HowItWorksView, FAQView

app_name = 'info'

urlpatterns = [
    path('', BlockchainInfoView.as_view(), name='blockchain_info'),
    path('how-it-works/', HowItWorksView.as_view(), name='how_it_works'),
    path('faq/', FAQView.as_view(), name='faq'),  # Added FAQ view
]