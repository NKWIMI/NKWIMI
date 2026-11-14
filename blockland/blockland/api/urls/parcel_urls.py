from django.urls import path, include
from django.contrib.auth.decorators import login_required
from registration.views import parcel_views as views  # << import the right module

urlpatterns = [
    path('', login_required(views.ParcelListView.as_view()), name='parcel_list'),
    path('create/', login_required(views.ParcelCreateView.as_view()), name='parcel_create'),
    path('<int:pk>/', include([
        path('', login_required(views.ParcelDetailView.as_view()), name='parcel_detail'),
        path('update/', login_required(views.ParcelUpdateView.as_view()), name='parcel_update'),
        #path('transfer/', login_required(views.ParcelTransferView.as_view()), name='parcel_transfer'),
    ])),
]
