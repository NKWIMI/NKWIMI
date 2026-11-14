from django.http import JsonResponse, HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, View
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.urls import reverse_lazy
from django.db.models import Q
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from reportlab.pdfgen import canvas
import io
from django.shortcuts import render
from registration.couchdb_client import get_or_create_db
from ..models import Transaction, User, Transfer, Parcel
from django.utils import timezone
import logging
import hashlib
import time

# Import ALL the forms you have defined
from ..forms.transfer_forms import (
    InitiateTransferForm, 
    SenderApproveTransferForm,
    AcceptTransferForm, 
    CancelTransferForm, 
    RejectTransferForm
)
from registration.forms.parcel_forms import ParcelTransferForm, ParcelRegistrationForm
from registration.services.blockchain_service import BlockchainService, BlockchainServiceError
from ..forms.transfer_forms import DirectTransferForm
from ..models.transfer_models import Transfer
from ..services.file_hash_service import FileHashService

logger = logging.getLogger(__name__)

def string_to_bytes32(text):
    """Convert a string to bytes32 format"""
    if len(text) > 32:
        text = text[:32]
    return text.encode('utf-8').ljust(32, b'\0')

def bytes32_to_string(bytes_data):
    """Convert bytes32 back to string"""
    return bytes_data.rstrip(b'\0').decode('utf-8')

def sync_transfer_with_blockchain(transfer):
    """
    Sync transfer status with blockchain state
    Returns: (success: bool, message: str)
    """
    try:
        blockchain = BlockchainService()
        pending_data = blockchain.get_pending_transfer(transfer.parcel.land_id)
        
        if pending_data and pending_data.get('active', False):
            # Transfer is still pending on blockchain
            if transfer.status != Transfer.PENDING:
                transfer.status = Transfer.PENDING
                transfer.save()
                return True, "Synced with blockchain: transfer is pending"
            return True, "Status matches blockchain"
        else:
            # No active transfer on blockchain
            if transfer.status == Transfer.PENDING:
                transfer.status = Transfer.CANCELED
                transfer.save()
                return True, "Synced with blockchain: transfer canceled"
            return True, "Status matches blockchain"
            
    except Exception as e:
        logger.error(f"Failed to sync transfer {transfer.id} with blockchain: {e}")
        return False, f"Sync failed: {str(e)}"

def couchdb_health(request):
    try:
        db = get_or_create_db("parcels")
        info = {"db_name": db.name, "doc_count": db.info().get("doc_count", 0)}
        return JsonResponse({"ok": True, "parcels": info})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

def parcels_by_owner(request, owner_id: int):
    db = get_or_create_db("parcels")
    view = db.view("parcels/by_owner_id", key=int(owner_id), reduce=False, include_docs=True)
    docs = [row.doc for row in view]
    return JsonResponse({"count": len(docs), "results": docs})

# Transaction views
class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'registration/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

# Base admin view
class AdminBaseView(LoginRequiredMixin):
    login_url = '/admin/login/'
    redirect_field_name = 'redirect_to'

# Admin view for listing all transactions
class AdminViewTransactionsView(AdminBaseView, ListView):
    model = Transaction
    template_name = 'admin/admin_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transaction.objects.all().order_by('-date')
        
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user__id=user_id)

        parcel_id = self.request.GET.get('parcel')
        if parcel_id:
            queryset = queryset.filter(parcel__id=parcel_id)

        tx_type = self.request.GET.get('type')
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_transactions'] = self.get_queryset().count()
        context['users'] = User.objects.all()
        return context

# Transfer views
class TransferListView(LoginRequiredMixin, ListView):
    model = Transfer
    template_name = 'transfers/list.html'
    context_object_name = 'transfers'
    
    def get_queryset(self):
        return Transfer.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).order_by('-created_at')

class TransferDetailView(LoginRequiredMixin, DetailView):
    model = Transfer
    template_name = 'transfers/detail.html'
    context_object_name = 'transfer'
    
    def get_object(self, queryset=None):
        transfer = super().get_object(queryset)
        if transfer.sender != self.request.user and transfer.recipient != self.request.user:
            raise PermissionDenied("You don't have permission to view this transfer")
        return transfer
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        transfer = self.object
        
        try:
            blockchain = BlockchainService()
            pending_data = blockchain.get_pending_transfer(transfer.parcel.land_id)
            context['blockchain_status'] = pending_data
            
            # Check if database and blockchain are in sync
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
        
        # Add forms for actions
        context['sender_approve_form'] = SenderApproveTransferForm()
        context['accept_form'] = AcceptTransferForm()
        context['cancel_form'] = CancelTransferForm()
        context['reject_form'] = RejectTransferForm()
        
        return context

class TransferCreateView(LoginRequiredMixin, CreateView):
    model = Transfer
    form_class = ParcelTransferForm 
    template_name = 'transfers/create.html'
    success_url = reverse_lazy('transfer:transfer_list')  # Add the namespace!
    
    def get_form_kwargs(self):
        """Pass the user and admin status to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['is_admin'] = self.request.user.is_superuser or self.request.user.is_staff
        return kwargs

    def get_context_data(self, **kwargs):
        """Add debug information to context"""
        context = super().get_context_data(**kwargs)
        
        # Debug: Show user's parcels
        user_parcels = Parcel.objects.filter(owner=self.request.user)
        context['debug_user_parcels'] = user_parcels
        context['debug_user_address'] = self.request.user.blockchain_address
        
        logger.debug(f"User {self.request.user.username} has {user_parcels.count()} parcels")
        logger.debug(f"Parcel queryset: {list(user_parcels.values_list('land_id', flat=True))}")
        
        return context
        
    def form_valid(self, form):
        logger.debug("=== TRANSFER DEBUG START ===")
        
        try:
            transfer = form.save(commit=False)
            transfer.sender = self.request.user
            
            # Get addresses
            recipient_address = transfer.recipient.blockchain_address
            sender_address = self.request.user.blockchain_address
            
            if not recipient_address:
                messages.error(self.request, "Recipient does not have a blockchain address")
                return self.form_invalid(form)
            
            # Initialize blockchain service
            blockchain = BlockchainService(user=self.request.user)
            
            # Check parcel ownership first
            parcel_data = blockchain.get_parcel(transfer.parcel.land_id)
            if not parcel_data or not parcel_data.get('exists'):
                messages.error(self.request, f"Parcel {transfer.parcel.land_id} not found on blockchain")
                return self.form_invalid(form)
            
            # Get the actual owner from blockchain
            actual_owner = parcel_data['owner']
            logger.debug(f"Actual parcel owner: {actual_owner}")
            logger.debug(f"Current user address: {sender_address}")
            
            # WALLET SWITCHING LOGIC - ONLY ONCE!
            if actual_owner.lower() != sender_address.lower():
                logger.info(f"🔄 Switching to parcel owner's wallet: {actual_owner}")
                
                # Find which user owns this parcel and switch to their wallet
                parcel_owner = User.objects.filter(blockchain_address__iexact=actual_owner).first()
                if parcel_owner:
                    # Switch to the parcel owner's wallet
                    blockchain = BlockchainService(user=parcel_owner)
                    sender_address = parcel_owner.blockchain_address
                    logger.info(f"✅ Switched to parcel owner wallet: {sender_address}")
                else:
                    messages.error(self.request, 
                        f"You are not the owner of this parcel. Parcel is owned by: {actual_owner}")
                    return self.form_invalid(form)
            
            # Create document hash
            import hashlib
            import json
            transfer_data = {
                'parcel_id': transfer.parcel.land_id,
                'from': sender_address,
                'to': recipient_address,
                'timestamp': timezone.now().isoformat(),
            }
            document_hash = hashlib.sha256(json.dumps(transfer_data).encode()).hexdigest()
            
            # Initiate transfer with the correct wallet
            tx_hash = blockchain.initiate_transfer(
                parcel_id=transfer.parcel.land_id,
                to_address=recipient_address,
                document_hash=document_hash
            )
            
            if tx_hash:
                transfer.transaction_hash = tx_hash
                transfer.status = Transfer.PENDING
                transfer.ipfs_hash = document_hash
                transfer.blockchain_initiated = True
                transfer.save()
                
                messages.success(self.request, f"Transfer initiated! Transaction: {tx_hash}")
                return redirect(self.success_url)
            else:
                messages.error(self.request, "Failed to initiate transfer on blockchain")
                return self.form_invalid(form)
            
        except Exception as e:
            logger.error(f"Transfer failed: {str(e)}")
            messages.error(self.request, f'Transfer failed: {str(e)}')
            return self.form_invalid(form)

class TransferAcceptView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        transfer = get_object_or_404(Transfer, pk=kwargs['pk'])
        
        print(f"=== TRANSFER ACCEPT DEBUG ===")
        print(f"Transfer ID: {transfer.id}")
        print(f"Current user: {request.user.username}")
        print(f"Transfer sender: {transfer.sender.username}")
        print(f"Transfer recipient: {transfer.recipient.username}")
        print(f"Current status: {transfer.status}")
        print(f"Sender approved: {transfer.sender_approved}")
        print(f"Recipient approved: {transfer.recipient_approved}")
        
        # Check if user is involved in this transfer
        if request.user != transfer.sender and request.user != transfer.recipient:
            raise PermissionDenied("You are not involved in this transfer")
        
        try:
            # Use the model's approval methods
            if request.user == transfer.sender:
                # SENDER approval
                if transfer.can_be_approved_by(request.user):
                    transfer.approve_by_sender()
                    messages.success(request, "Transfer approved successfully! Waiting for recipient acceptance.")
                else:
                    messages.error(request, "You cannot approve this transfer at this time")
                    
            elif request.user == transfer.recipient:
                # RECIPIENT approval - this is where blockchain execution happens
                if transfer.can_be_approved_by(request.user):
                    
                    # First, update the database status
                    transfer.approve_by_recipient()
                    
                    # If both parties have approved, execute blockchain transfer
                    if transfer.status == Transfer.COMPLETED:
                        try:
                            # FORCE WALLET SWITCHING - CRITICAL FIX!
                            blockchain = BlockchainService(user=request.user)
                            
                            # Check if we need to switch to the correct wallet
                            if request.user.blockchain_address and blockchain.account.address.lower() != request.user.blockchain_address.lower():
                                logger.info(f"🔄 Force switching to user's actual wallet: {request.user.blockchain_address}")
                                if not blockchain.switch_to_user_wallet(request.user):
                                    messages.error(request, "Failed to switch to your wallet. Please contact administrator.")
                                    return redirect('transfer:transfer_detail', pk=transfer.pk)
                            
                            # Check if there's a pending transfer on blockchain
                            pending_data = blockchain.get_pending_transfer(transfer.parcel.land_id)
                            if not pending_data or not pending_data.get('active', False):
                                messages.error(request, "No pending transfer found on blockchain. The transfer may have been canceled.")
                                return redirect('transfer:transfer_detail', pk=transfer.pk)
                            
                            # Execute the blockchain acceptance
                            tx_hash = blockchain.accept_transfer(transfer.parcel.land_id)
                            
                            if tx_hash:
                                transfer.transaction_hash = tx_hash
                                transfer.parcel.owner = transfer.recipient
                                transfer.parcel.save()
                                transfer.save()
                                
                                messages.success(request, f"Transfer completed successfully! Transaction: {tx_hash}")
                            else:
                                messages.error(request, "Failed to complete transfer on blockchain")
                                
                        except BlockchainServiceError as e:
                            logger.error(f"Blockchain acceptance failed: {e}")
                            messages.error(request, f"Transfer completion failed: {str(e)}")
                        except Exception as e:
                            logger.error(f"Unexpected error during acceptance: {e}")
                            messages.error(request, f"An unexpected error occurred: {str(e)}")
                    else:
                        messages.success(request, "Transfer accepted successfully! Waiting for sender approval.")
                else:
                    messages.error(request, "You cannot accept this transfer at this time")
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            messages.error(request, f"An unexpected error occurred: {str(e)}")
        
        return redirect('transfer:transfer_detail', pk=transfer.pk)
class TransferCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        transfer = get_object_or_404(Transfer, pk=kwargs['pk'])
        
        if transfer.sender != request.user:
            raise PermissionDenied("Only the sender can cancel a transfer")
        
        if transfer.status != Transfer.PENDING:
            messages.error(request, "Transfer is not in pending status")
            return redirect('transfer_detail', pk=transfer.pk)
        
        try:
            blockchain = BlockchainService(user=request.user)
            tx_hash = blockchain.cancel_transfer(transfer.parcel.land_id)
            
            if tx_hash:
                transfer.status = Transfer.CANCELED
                transfer.save()
                messages.success(request, f"Transfer cancelled successfully! Transaction: {tx_hash}")
            else:
                messages.error(request, "Failed to cancel transfer on blockchain")
                
        except Exception as e:
            messages.error(request, f"Failed to cancel transfer: {str(e)}")
        
        return redirect('transfer_detail', pk=transfer.pk)

class TransferRejectView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        transfer = get_object_or_404(Transfer, pk=kwargs['pk'])
        
        if transfer.recipient != request.user:
            raise PermissionDenied("You are not the recipient of this transfer")
        
        if transfer.status != Transfer.PENDING:
            messages.error(request, "Transfer is not in pending status")
            return redirect('transfer_detail', pk=transfer.pk)
        
        try:
            blockchain = BlockchainService(user=request.user)
            
            # For rejection, we'll use cancelTransfer since there's no rejectTransfer in your ABI
            tx_hash = blockchain.cancel_transfer(transfer.parcel.land_id)
            
            if tx_hash:
                transfer.status = Transfer.REJECTED
                transfer.save()
                messages.success(request, f"Transfer rejected successfully! Transaction: {tx_hash}")
            else:
                # If blockchain operation fails, still update the database
                transfer.status = Transfer.REJECTED
                transfer.save()
                messages.success(request, "Transfer rejected in database (blockchain operation failed)")
            
        except Exception as e:
            logger.error(f"Transfer rejection failed: {e}")
            # If blockchain operation fails, still update the database
            transfer.status = Transfer.REJECTED
            transfer.save()
            messages.success(request, "Transfer rejected in database (blockchain operation failed)")
        
        return redirect('transfer_detail', pk=transfer.pk)

class TransferHistoryView(LoginRequiredMixin, ListView):
    model = Transfer
    template_name = 'transfers/history.html'
    context_object_name = 'transfers'
    paginate_by = 10

    def get_queryset(self):
        # Get all transfers where user is either sender or recipient
        transfers = Transfer.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        ).select_related('sender', 'recipient', 'parcel').order_by('-created_at')
        
        return transfers

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add additional context for the template
        context['page_title'] = 'Transfer History'
        context['active_tab'] = 'history'
        
        return context

class TransferPrintView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        transfer = get_object_or_404(Transfer, pk=kwargs['pk'])
        
        if transfer.sender != request.user and transfer.recipient != request.user:
            raise PermissionDenied("You don't have permission to view this transfer")
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="transfer_{transfer.id}.pdf"'
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        
        p.drawString(100, 800, f"Transfer Document #{transfer.id}")
        p.drawString(100, 780, f"Parcel: {transfer.parcel.land_id}")
        p.drawString(100, 760, f"From: {transfer.sender.username}")
        p.drawString(100, 740, f"To: {transfer.recipient.username}")
        p.drawString(100, 720, f"Status: {transfer.status}")
        p.drawString(100, 700, f"Created: {transfer.created_at}")
        
        if transfer.transaction_hash:
            p.drawString(100, 680, f"Blockchain TX: {transfer.transaction_hash}")
        
        p.showPage()
        p.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response