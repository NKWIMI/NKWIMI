# registration/views/admin_views.py
from django.views.generic import (
    TemplateView, ListView, DetailView, View,
    CreateView, UpdateView, DeleteView, FormView
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
import io
import csv
import os
from reportlab.pdfgen import canvas
import logging
from django.db.models import Q
from django.db import models
from ..models.parcel_models import Parcel, ParcelMetadata
from ..models.transaction_models import Transaction
from ..models.transfer_models import Transfer

from web3 import Web3
import secrets
# Import forms directly from their modules
from registration.forms.parcel_forms import ParcelTransferForm, ParcelRegistrationForm
from ..forms.profile_forms import UserForm

from ..models import AuditLog
from ..services.blockchain_service import BlockchainService
from ..services.file_hash_service import FileHashService
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from registration.models.user_models import User

logger = logging.getLogger(__name__)

# ========================
# BASE ADMIN VIEW CLASSES
# ========================

class AdminBaseView(LoginRequiredMixin, UserPassesTestMixin):
    """Base class for all admin views with authentication and permission checks"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


# ========================
# DASHBOARD & CORE VIEWS
# ========================

class AdminDashboardView(AdminBaseView, TemplateView):
    """Admin dashboard overview"""
    template_name = 'admin/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user_count': User.objects.count(),
            'parcel_count': Parcel.objects.count(),
            'transfer_count': Transfer.objects.count(),
            'recent_activity': AuditLog.objects.order_by('-timestamp')[:5],
            'recent_transfers': Transfer.objects.order_by('-created_at')[:5]
        })
        return context


class SecuritySettingsView(AdminBaseView, TemplateView):
    """Admin security settings page"""
    template_name = 'admin/admin_security_settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Password policy settings
        context['password_policy'] = {
            'min_length': 8,
            'require_numbers': True,
            'require_special': True,
            'require_uppercase': True,
            'expiration_days': 90
        }

        # Two-factor authentication status
        context['two_factor_enabled'] = False

        # Recent security events
        recent_logs = AuditLog.objects.filter(
            action_type__in=['login_failed', 'unauthorized_access', 'password_change'],
            timestamp__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-timestamp')[:20]
        context['recent_security_events'] = recent_logs

        # Blockchain security settings
        context['blockchain_settings'] = {
            'require_owner_confirmation': True,
            'auto_audit_enabled': True,
            'transaction_alert_email': 'admin@example.com'
        }

        return context


# ========================
# USER MANAGEMENT VIEWS
# ========================

class AdminManageUsersView(AdminBaseView, ListView):
    """List and manage all users"""
    model = User
    template_name = 'admin/manage_users.html'
    context_object_name = 'users'
    paginate_by = 20
    ordering = ['-date_joined']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if search := self.request.GET.get('search'):
            return queryset.filter(username__icontains=search)
        return queryset


class AdminUserDetailView(AdminBaseView, DetailView):
    """View detailed user information"""
    model = User
    template_name = 'admin/user_detail.html'
    context_object_name = 'user_detail'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context.update({
            'parcels_owned': Parcel.objects.filter(owner=user),
            'transfers_sent': Transfer.objects.filter(sender=user),
            'transfers_received': Transfer.objects.filter(recipient=user),
            'activity_logs': AuditLog.objects.filter(user=user)[:10]
        })
        return context


class AdminVerifyUserView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin view to verify a user"""
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        from registration.models import User
        return User.objects.all()
    
    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        return obj
    
    def post(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            user.is_verified = True
            user.verified_by = request.user
            user.verified_at = timezone.now()
            user.save()
            
            messages.success(request, f'User {user.username} has been verified successfully.')
        except Exception as e:
            messages.error(request, f'Error verifying user: {str(e)}')
        
        return redirect('admin_users')

class AdminUserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = 'registration/admin_create_user.html'
    success_url = reverse_lazy('admin_panel:admin_manage_users') 
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def form_valid(self, form):
        try:
            # Generate blockchain wallet BEFORE saving
            private_key = "0x" + secrets.token_hex(32)
            account = Web3().eth.account.from_key(private_key)
            
            # Create user with wallet
            user = form.save(commit=False)
            user.blockchain_address = account.address
            user.encrypted_private_key = private_key  # For development
            user.save()
            
            # Fund the wallet in development
            if settings.DEBUG:
                try:
                    blockchain = BlockchainService()
                    blockchain.fund_user_account(account.address, 2.0)  # Fund with 2 ETH
                except Exception as e:
                    logger.warning(f"Could not auto-fund user wallet: {e}")
            
            # Log the action
            AuditLog.objects.create(
                user=self.request.user,
                action='USER_CREATED',
                content_object=user,
                details={
                    'created_by': self.request.user.username,
                    'wallet_address': account.address,
                    'auto_funded': settings.DEBUG
                }
            )
            
            messages.success(self.request, f'User {user.username} created successfully with wallet: {account.address}')
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Error creating user with wallet: {e}")
            messages.error(self.request, f'Error creating user: {str(e)}')
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New User'
        context['is_create'] = True
        context['is_admin'] = True
        return context
class AdminUserUpdateView(AdminBaseView, UpdateView):
    """Update user account information"""
    model = User
    form_class = UserForm
    template_name = 'registration/admin_create_user.html'
    
    def form_valid(self, form):
        user = form.save()
        AuditLog.objects.create(
            user=self.request.user, 
            action='USER_UPDATED', 
            content_object=user,
            details={'updated_by': self.request.user.username}
        )
        messages.success(self.request, f'User {user.username} updated successfully!')
        return redirect('admin_panel:admin_user_detail', pk=user.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Update User'
        context['is_create'] = False
        return context

class AdminUserDeleteView(AdminBaseView, DeleteView):
    """Delete a user account"""
    model = User
    template_name = 'admin/user_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:admin_manage_users')
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        AuditLog.objects.create(
            user=request.user, 
            action='USER_DELETED', 
            content_object=user,
            details={'deleted_by': request.user.username}
        )
        return super().delete(request, *args, **kwargs)


# ========================
# PARCEL MANAGEMENT VIEWS
# ========================

class AdminManageParcelsView(AdminBaseView, ListView):
    """List and manage all parcels"""
    model = Parcel
    template_name = 'admin/manage_parcels.html'
    context_object_name = 'parcels'
    paginate_by = 20
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if status := self.request.GET.get('status'):
            return queryset.filter(status=status)
        return queryset


class AdminParcelDetailView(AdminBaseView, DetailView):
    """View detailed parcel information"""
    model = Parcel
    template_name = 'registration/parcel_detail.html'
    context_object_name = 'parcel'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parcel = self.get_object()
        context.update({
            'metadata_versions': parcel.metadata_versions.all().order_by('-created_at'),
            'transfers': Transfer.objects.filter(parcel=parcel).order_by('-created_at'),
        })
        return context


# ========================
# TRANSFER MANAGEMENT VIEWS (NEW)
# ========================

# In your admin_views.py - Update the AdminTransferHistoryView

class AdminTransferHistoryView(AdminBaseView, ListView):
    """Admin view to see ALL transfers in the system"""
    model = Transfer
    template_name = 'admin/transfers/transfer_history.html'
    context_object_name = 'transfers'
    paginate_by = 20
    ordering = ['-created_at']
    
    def get_template_names(self):
        """Only use our custom template, don't fall back to model-based templates"""
        return [self.template_name]
    
    def get_queryset(self):
        """Admin sees all transfers, not just their own"""
        queryset = Transfer.objects.all().select_related('sender', 'recipient', 'parcel')
        
        # Filter by status if provided
        if status := self.request.GET.get('status'):
            queryset = queryset.filter(status=status)
            
        # Filter by parcel if provided
        if parcel_id := self.request.GET.get('parcel'):
            queryset = queryset.filter(parcel__land_id__icontains=parcel_id)
            
        # Filter by user if provided
        if user_id := self.request.GET.get('user'):
            queryset = queryset.filter(
                Q(sender_id=user_id) | Q(recipient_id=user_id)
            )
            
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['total_transfers'] = queryset.count()
        context['pending_transfers'] = queryset.filter(status=Transfer.PENDING).count()
        context['completed_transfers'] = queryset.filter(status=Transfer.COMPLETED).count()
        
        # Add users for filter dropdown
        context['all_users'] = User.objects.all()
        return context

class AdminTransferDetailView(AdminBaseView, DetailView):
    """Admin view for transfer details"""
    model = Transfer
    template_name = 'admin/transfers/transfer_detail.html'
    context_object_name = 'transfer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transfer = self.get_object()
        
        try:
            blockchain = BlockchainService()
            pending_data = blockchain.get_pending_transfer(transfer.parcel.land_id)
            context['blockchain_status'] = pending_data
            
            # Check sync status
            is_active_on_blockchain = pending_data.get('active', False)
            is_pending_in_db = transfer.status == Transfer.PENDING
            
            context['sync_status'] = {
                'in_sync': is_active_on_blockchain == is_pending_in_db,
                'blockchain_active': is_active_on_blockchain,
                'db_pending': is_pending_in_db,
                'needs_sync': is_active_on_blockchain != is_pending_in_db
            }
            
        except Exception as e:
            context['blockchain_error'] = str(e)
            context['sync_status'] = {'in_sync': False, 'error': str(e)}
        
        return context


class AdminForceSyncTransferView(AdminBaseView, View):
    """Admin view to force sync a transfer with blockchain"""
    
    def post(self, request, *args, **kwargs):
        transfer = get_object_or_404(Transfer, pk=kwargs['pk'])
        
        try:
            from ..views.transfer_views import sync_transfer_with_blockchain
            success, message = sync_transfer_with_blockchain(transfer)
            
            if success:
                messages.success(request, f"Transfer synced: {message}")
            else:
                messages.error(request, f"Sync failed: {message}")
                
        except Exception as e:
            messages.error(request, f"Sync error: {str(e)}")
            
        return redirect('admin_panel:admin_transfer_detail', pk=transfer.pk)


# ========================
# PARCEL CONTRACT VIEWER
# ========================

class AdminParcelContractView(AdminBaseView, DetailView):
    """Admin view for parcel contract documents"""
    model = Parcel
    template_name = 'admin/parcel_contract.html'
    context_object_name = 'parcel'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parcel = self.get_object()
        
        # Add contract file information
        if parcel.contract_file:
            context['contract_file'] = parcel.contract_file
            context['contract_url'] = parcel.contract_file.url
        
        return context


class AdminParcelCreateView(AdminBaseView, CreateView):
    """Create a new parcel"""
    model = Parcel
    form_class = ParcelRegistrationForm
    template_name = 'admin/parcel_form.html'
    success_url = reverse_lazy('admin_panel:admin_manage_parcels')

    def form_valid(self, form):
        try:
            parcel = form.save(commit=False)
            parcel.owner = self.request.user.profile
            parcel.owner_address = self.request.user.blockchain_address

            # File upload to IPFS
            if 'contract_file' in self.request.FILES:
                file_service = FileHashService()
                parcel.latest_ipfs_hash = file_service.add_file(self.request.FILES['contract_file'])

            parcel.save()

            # Register on blockchain
            blockchain = BlockchainService(self.request.user)
            tx_hash = blockchain.register_parcel(
                parcel.land_id, 
                parcel.owner_address, 
                parcel.latest_ipfs_hash or ''
            )
            parcel.transaction_hash = tx_hash
            parcel.save(update_fields=['transaction_hash'])

            ParcelMetadata.objects.create(
                parcel=parcel,
                ipfs_hash=parcel.latest_ipfs_hash or '',
                uploader=self.request.user,
                notes="Initial registration (admin)",
            )

            AuditLog.objects.create(
                user=self.request.user, 
                action='PARCEL_CREATED', 
                content_object=parcel,
                details={'created_by': self.request.user.username}
            )
            return redirect(self.success_url)
        except Exception as e:
            logger.error(f"Error creating parcel: {e}", exc_info=True)
            form.add_error(None, str(e))
            return super().form_invalid(form)


class AdminParcelUpdateView(AdminBaseView, UpdateView):
    """Update parcel information"""
    model = Parcel
    form_class = ParcelRegistrationForm
    template_name = 'admin/parcel_form.html'
    success_url = reverse_lazy('admin_panel:admin_manage_parcels')

    def form_valid(self, form):
        try:
            parcel = form.save(commit=False)

            if 'contract_file' in self.request.FILES:
                file_service = FileHashService()
                new_hash = file_service.add_file(self.request.FILES['contract_file'])
                if new_hash != parcel.latest_ipfs_hash:
                    ParcelMetadata.objects.create(
                        parcel=parcel,
                        ipfs_hash=new_hash,
                        uploader=self.request.user,
                        notes=form.cleaned_data.get('change_notes', 'Document updated'),
                    )
                    parcel.latest_ipfs_hash = new_hash

            parcel.save()
            AuditLog.objects.create(
                user=self.request.user, 
                action='PARCEL_UPDATED', 
                content_object=parcel,
                details={'updated_by': self.request.user.username}
            )
            return redirect(self.success_url)
        except Exception as e:
            logger.error(f"Error updating parcel: {e}", exc_info=True)
            form.add_error(None, str(e))
            return super().form_invalid(form)


class AdminParcelDeleteView(AdminBaseView, DeleteView):
    """Delete a parcel"""
    model = Parcel
    template_name = 'admin/parcel_confirm_delete.html'
    success_url = reverse_lazy('admin_panel:admin_manage_parcels')

    def delete(self, request, *args, **kwargs):
        parcel = self.get_object()
        AuditLog.objects.create(
            user=self.request.user, 
            action='PARCEL_DELETED', 
            content_object=parcel,
            details={'deleted_by': self.request.user.username}
        )
        return super().delete(request, *args, **kwargs)


class AdminParcelTransferView(AdminBaseView, FormView):
    """Initiate a parcel transfer"""
    template_name = 'admin/parcel_transfer.html'
    form_class = ParcelTransferForm
    
    def form_valid(self, form):
        try:
            sender_parcel = form.cleaned_data['parcel']
            recipient_user = form.cleaned_data['recipient_user']

            # Check if parcel is properly registered
            blockchain = BlockchainService()
            if not blockchain.is_parcel_registered(sender_parcel.land_id):
                messages.error(self.request, f"Parcel {sender_parcel.land_id} is not registered on blockchain")
                return self.form_invalid(form)

            blockchain_service = BlockchainService(self.request.user)
            tx_hash = blockchain_service.initiate_transfer(
                land_id=str(sender_parcel.id),
                recipient_address=recipient_user.blockchain_address,
                document_hash=sender_parcel.latest_ipfs_hash or ''
            )

            AuditLog.objects.create(
                user=self.request.user,
                action='PARCEL_TRANSFER_INITIATED',
                content_object=sender_parcel,
                details={'tx_hash': tx_hash, 'recipient': recipient_user.username}
            )
            
            messages.success(self.request, f"Transfer initiated! Transaction: {tx_hash}")
            return redirect('admin_panel:admin_manage_parcels')
            
        except Exception as e:
            logger.error(f"Error transferring parcel: {e}", exc_info=True)
            messages.error(self.request, f"Transfer failed: {str(e)}")
            return super().form_invalid(form)


# ========================
# TRANSACTION & LOG VIEWS
# ========================

class AdminViewTransactionsView(AdminBaseView, ListView):
    """View all system transactions"""
    model = Transaction
    template_name = 'admin/admin_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            return queryset.filter(
                parcel__land_id__icontains=search
            ) | queryset.filter(
                sender__username__icontains=search
            ) | queryset.filter(
                recipient__username__icontains=search
            )
        return queryset


class AdminViewLogsView(AdminBaseView, TemplateView):
    """View system logs"""
    template_name = 'admin/view_logs.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        db_logs = AuditLog.objects.order_by('-timestamp')[:100]
        file_logs = []
        error_message = None
        log_file_path = getattr(settings, 'LOG_FILE_PATH', None)
        
        if log_file_path and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r', encoding='utf-8') as log_file:
                    file_logs = list(reversed(list(log_file)))[:100]
            except Exception as e:
                error_message = str(e)
                
        context.update({
            'db_logs': db_logs,
            'file_logs': file_logs,
            'log_file_path': log_file_path,
            'error_message': error_message,
            'last_refreshed': timezone.now()
        })
        return context


# ========================
# REPORT GENERATION VIEWS
# ========================

class AdminGenerateReportsView(AdminBaseView, TemplateView):
    """Report generation dashboard"""
    template_name = 'admin/generate_reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'user_count': User.objects.count(),
            'parcel_count': Parcel.objects.count(),
            'transfer_count': Transfer.objects.count(),
        })
        return context


class GenerateUserReportView(AdminBaseView, View):
    """Generate user activity report"""
    def post(self, request, *args, **kwargs):
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="user_activity_report.pdf"'
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, "User Activity Report")
        
        qs = User.objects.all()
        if start_date and end_date:
            qs = qs.filter(date_joined__range=[start_date, end_date])
            
        p.drawString(100, 780, f"Users in range: {qs.count()}")
        y = 750
        
        for user in qs[:50]:
            p.drawString(100, y, f"- {user.username} ({user.email})")
            y -= 20
            if y < 50:
                p.showPage()
                y = 800
                
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response


class GenerateParcelReportView(AdminBaseView, View):
    """Generate parcel transactions report"""
    def post(self, request, *args, **kwargs):
        parcel_id = request.POST.get("parcel_id")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="parcel_transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(["Parcel ID", "Owner", "Created", "Status", "Latest IPFS Hash", "Transaction Hash"])
        
        qs = Parcel.objects.all()
        if parcel_id:
            qs = qs.filter(id=parcel_id)
            
        for parcel in qs:
            writer.writerow([
                parcel.id,
                parcel.owner.user.username if parcel.owner else "N/A",
                parcel.created_at,
                parcel.status,
                parcel.latest_ipfs_hash or '',
                parcel.transaction_hash or ''
            ])
        return response


class GenerateTransferReportView(AdminBaseView, View):
    """Generate transfer report for admin"""
    def post(self, request, *args, **kwargs):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="transfer_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(["Transfer ID", "Parcel", "Sender", "Recipient", "Status", "Created", "Transaction Hash"])
        
        transfers = Transfer.objects.all().select_related('parcel', 'sender', 'recipient')
        
        for transfer in transfers:
            writer.writerow([
                transfer.id,
                transfer.parcel.land_id,
                transfer.sender.username,
                transfer.recipient.username,
                transfer.get_status_display(),
                transfer.created_at,
                transfer.transaction_hash or ''
            ])
        return response


class GenerateSystemReportView(AdminBaseView, View):
    """Generate system statistics report"""
    def post(self, request, *args, **kwargs):
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="system_statistics.pdf"'
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, "System Statistics Report")
        p.drawString(100, 780, f"Users: {User.objects.count()}")
        p.drawString(100, 760, f"Parcels: {Parcel.objects.count()}")
        p.drawString(100, 740, f"Transfers: {Transfer.objects.count()}")
        p.drawString(100, 720, f"Pending Transfers: {Transfer.objects.filter(status=Transfer.PENDING).count()}")
        
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response


# ========================
# REGULAR USER VIEWS
# ========================

class UserDashboardView(LoginRequiredMixin, TemplateView):
    """Regular user dashboard view (not admin-specific)"""
    template_name = 'registration/dashboard/user_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'page_title': 'User Dashboard - Blockland',
            'user_parcels': Parcel.objects.filter(owner=user)[:5],
            'recent_transfers': Transfer.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).order_by('-timestamp')[:5],
            'user_activity': AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
        })
        return context
# Add this to your admin_views.py temporarily

class AdminTransferDebugView(AdminBaseView, TemplateView):
    """Debug view to check transfer data"""
    template_name = 'admin/transfer_debug.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all transfers with detailed information
        transfers = Transfer.objects.all().select_related('sender', 'recipient', 'parcel')
        
        transfer_data = []
        for transfer in transfers:
            transfer_data.append({
                'id': transfer.id,
                'parcel_id': transfer.parcel.id if transfer.parcel else None,
                'parcel_land_id': transfer.parcel.land_id if transfer.parcel else 'No Parcel',
                'sender_id': transfer.sender.id if transfer.sender else None,
                'sender_username': transfer.sender.username if transfer.sender else 'No Sender',
                'recipient_id': transfer.recipient.id if transfer.recipient else None,
                'recipient_username': transfer.recipient.username if transfer.recipient else 'No Recipient',
                'status': transfer.status,
                'created_at': transfer.created_at,
                'transaction_hash': transfer.transaction_hash,
            })
        
        context.update({
            'transfer_count': transfers.count(),
            'transfers': transfer_data,
            'user_count': User.objects.count(),
            'parcel_count': Parcel.objects.count(),
        })
        
        return context