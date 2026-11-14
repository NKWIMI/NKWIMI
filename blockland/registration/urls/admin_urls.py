# registration/urls/admin_urls.py
from django.urls import path
from registration.views.admin_views import (
    AdminDashboardView, SecuritySettingsView,
    AdminManageUsersView, AdminUserDetailView, AdminUserCreateView, 
    AdminUserUpdateView, AdminUserDeleteView, AdminVerifyUserView,
    AdminManageParcelsView, AdminParcelDetailView, AdminParcelCreateView,
    AdminParcelUpdateView, AdminParcelDeleteView, AdminParcelTransferView,
    AdminViewTransactionsView, AdminViewLogsView,
    AdminGenerateReportsView, GenerateUserReportView, GenerateParcelReportView,
    GenerateSystemReportView, GenerateTransferReportView,
    AdminTransferHistoryView, AdminTransferDetailView, AdminForceSyncTransferView
)

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('security/', SecuritySettingsView.as_view(), name='admin_security'),
    
    # User Management
    path('users/', AdminManageUsersView.as_view(), name='admin_manage_users'),
    path('users/create/', AdminUserCreateView.as_view(), name='admin_user_create'),
    path('users/<int:pk>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('users/<int:pk>/update/', AdminUserUpdateView.as_view(), name='admin_user_update'),
    path('users/<int:pk>/delete/', AdminUserDeleteView.as_view(), name='admin_user_delete'),
    path('users/<int:pk>/verify/', AdminVerifyUserView.as_view(), name='admin_verify_user'),
    
    # Parcel Management
    path('parcels/', AdminManageParcelsView.as_view(), name='admin_manage_parcels'),
    path('parcels/create/', AdminParcelCreateView.as_view(), name='admin_parcel_create'),
    path('parcels/<int:pk>/', AdminParcelDetailView.as_view(), name='admin_parcel_detail'),
    path('parcels/<int:pk>/update/', AdminParcelUpdateView.as_view(), name='admin_parcel_update'),
    path('parcels/<int:pk>/delete/', AdminParcelDeleteView.as_view(), name='admin_parcel_delete'),
    path('parcels/transfer/', AdminParcelTransferView.as_view(), name='admin_parcel_transfer'),
    
    # Transfer Management
    path('transfers/', AdminTransferHistoryView.as_view(), name='admin_transfer_history'),
    path('transfers/<int:pk>/', AdminTransferDetailView.as_view(), name='admin_transfer_detail'),
    path('transfers/<int:pk>/sync/', AdminForceSyncTransferView.as_view(), name='admin_transfer_sync'),
        
    # Transactions & Logs
    path('transactions/', AdminViewTransactionsView.as_view(), name='admin_transactions'),
    path('logs/', AdminViewLogsView.as_view(), name='admin_logs'),  # This is the correct name
    
    # Reports
    path('reports/', AdminGenerateReportsView.as_view(), name='admin_reports'),  # This is the correct name
    path('reports/users/', GenerateUserReportView.as_view(), name='admin_report_users'),
    path('reports/parcels/', GenerateParcelReportView.as_view(), name='admin_report_parcels'),
    path('reports/transfers/', GenerateTransferReportView.as_view(), name='admin_report_transfers'),
    path('reports/system/', GenerateSystemReportView.as_view(), name='admin_report_system'),
]