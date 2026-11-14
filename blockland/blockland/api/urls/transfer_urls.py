from django.urls import path
from django.contrib.auth.decorators import login_required
from registration.views import transfer_views as views

urlpatterns = [
    path('', login_required(views.TransferListView.as_view()), name='transfer_list'),
    path('create/', login_required(views.TransferCreateView.as_view()), name='transfer_create'),
    path('<int:pk>/accept/', login_required(views.TransferAcceptView.as_view()), name='transfer_accept'),
    path('<int:pk>/reject/', login_required(views.TransferRejectView.as_view()), name='transfer_reject'),
]
