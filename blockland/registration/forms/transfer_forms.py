# registration/forms/transfer_forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.apps import apps  # ADD THIS IMPORT
import logging
import os

from ..models.transfer_models import Transfer
from ..models.audit_models import AuditLog
from ..models.parcel_models import Parcel
from ..services.blockchain_service import BlockchainService
from ..services.file_hash_service import FileHashService

logger = logging.getLogger(__name__)
User = get_user_model()

class InitiateTransferForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'placeholder': 'Select recipient',
            'id': 'id_recipient'
        }),
        help_text="User who will receive the parcel (must have blockchain address)"
    )
    
    transfer_contract_file = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'
        }),
        help_text="Signed transfer agreement document (max 10MB)"
    )
    
    terms = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Optional transfer terms and conditions...'
        }),
        help_text="Additional terms for this transfer"
    )

    class Meta:
        model = Transfer
        fields = ['parcel', 'recipient', 'terms', 'transfer_contract_file']
        widgets = {
            'parcel': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_parcel'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.is_admin = kwargs.pop('is_admin', False)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get users with blockchain addresses
            all_users = User.objects.exclude(blockchain_address__isnull=True).exclude(blockchain_address='')
            
            if self.is_admin:
                parcels = Parcel.objects.filter(is_frozen=False).select_related('owner')
                recipients = all_users
            else:
                # Only show parcels owned by the current user
                parcels = Parcel.objects.filter(owner=self.user, is_frozen=False)
                recipients = all_users.exclude(id=self.user.id)
            
            self.fields['parcel'].queryset = parcels
            self.fields['recipient'].queryset = recipients
            
            # Add helpful messages if no parcels available
            if parcels.count() == 0 and not self.is_admin:
                self.fields['parcel'].empty_label = "No parcels available - you don't own any parcels"
            else:
                self.fields['parcel'].empty_label = "Select a parcel to transfer"

    def clean(self):
        cleaned_data = super().clean()
        parcel = cleaned_data.get('parcel')
        recipient = cleaned_data.get('recipient')
        
        if parcel and recipient:
            # Enhanced ownership validation
            is_owner = False
            
            # Method 1: Check owner field
            if hasattr(parcel, 'owner') and parcel.owner == self.user:
                is_owner = True
                logger.debug(f"Ownership validated via owner field: {parcel.owner.username}")
            
            # Method 2: Check blockchain address
            elif hasattr(parcel, 'owner_address') and self.user.blockchain_address:
                if parcel.owner_address.lower() == self.user.blockchain_address.lower():
                    is_owner = True
                    logger.debug(f"Ownership validated via blockchain address: {self.user.blockchain_address}")
            
            # Debug logging
            logger.debug(f"Transfer ownership check - User: {self.user.username}, Parcel owner: {parcel.owner.username if parcel.owner else 'None'}, Is owner: {is_owner}")
            
            if parcel.owner == recipient:
                raise ValidationError("Cannot transfer parcel to the current owner")
                
            if not recipient.blockchain_address:
                raise ValidationError("Recipient must have a blockchain address configured")
                
            # Additional validation for non-admin users
            if not self.is_admin and not is_owner:
                raise ValidationError(
                    f"You can only transfer parcels that you own. "
                    f"This parcel is owned by {parcel.owner.username}."
                )
                
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.sender = self.user
        transfer.status = Transfer.PENDING
        
        # Upload contract file to IPFS
        if 'transfer_contract_file' in self.files:
            file_service = FileHashService()
            contract_file = self.files['transfer_contract_file']
            ipfs_hash = file_service.add_file(contract_file)
            transfer.contract_hash = ipfs_hash
        
        if commit:
            transfer.save()
            self._create_transfer_history(transfer, "Transfer initiated")
            self._send_transfer_notification(transfer)
            
        return transfer
    
    def _create_transfer_history(self, transfer, notes):
        """Create transfer history record"""
        try:
            # Check if TransferHistory model exists and create record
            TransferHistory = None
            try:
                TransferHistory = apps.get_model('registration', 'TransferHistory')
            except LookupError:
                logger.warning("TransferHistory model not found, skipping history creation")
                return
                
            if TransferHistory:
                TransferHistory.objects.create(
                    transfer=transfer,
                    from_user=transfer.sender,
                    to_user=transfer.recipient,
                    parcel=transfer.parcel,
                    status=transfer.status,
                    notes=notes
                )
        except Exception as e:
            logger.error(f"Failed to create transfer history: {e}")
    
    def _send_transfer_notification(self, transfer):
        """Send notification to recipient about pending transfer"""
        try:
            subject = f"Land Transfer Request - Parcel {transfer.parcel.land_id}"
            
            # Create message context
            context = {
                'transfer': transfer,
                'recipient': transfer.recipient,
                'sender': transfer.sender,
                'parcel': transfer.parcel,
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
            }
            
            # Try to render HTML template, fallback to plain text
            try:
                message = render_to_string('emails/transfer_request_notification.html', context)
            except:
                message = f"""
                You have received a land transfer request for parcel {transfer.parcel.land_id}.
                
                Sender: {transfer.sender.username}
                Parcel: {transfer.parcel.land_id}
                Location: {getattr(transfer.parcel, 'location', 'Not specified')}
                
                Please log in to review and accept this transfer.
                """
            
            send_mail(
                subject,
                message.strip(),
                settings.DEFAULT_FROM_EMAIL,
                [transfer.recipient.email],
                html_message=message if message != message.strip() else None,
                fail_silently=True,  # Don't raise errors if email fails
            )
            logger.info(f"Transfer notification sent to {transfer.recipient.email}")
        except Exception as e:
            logger.error(f"Failed to send transfer notification: {e}")

class SenderApproveTransferForm(forms.ModelForm):
    confirm_approval = forms.BooleanField(
        required=True,
        label="I confirm I approve this land transfer as the sender"
    )
    
    approval_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3, 
            'class': 'form-control',
            'placeholder': 'Optional approval notes...'
        }),
        label="Approval Notes"
    )

    class Meta:
        model = Transfer
        fields = []

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance or not self.instance.pk:
            raise ValidationError("Invalid transfer request")
        
        if self.user != self.instance.sender:
            raise ValidationError("Only the sender can approve this transfer")
        
        if self.instance.status != Transfer.PENDING:
            raise ValidationError("This transfer cannot be approved at this time")
        
        if self.instance.sender_approved:
            raise ValidationError("You have already approved this transfer")
        
        if not cleaned_data.get('confirm_approval'):
            raise ValidationError("You must confirm your approval")
        
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.sender_approved = True
        transfer.sender_approved_at = timezone.now()
        
        # Update status based on recipient's approval status
        if transfer.recipient_approved:
            transfer.status = Transfer.COMPLETED
            self._complete_transfer(transfer)
        else:
            transfer.status = Transfer.SENDER_APPROVED
        
        if commit:
            transfer.save()
            self._create_transfer_history(transfer, "Sender approved transfer")
            self._send_approval_notification(transfer, 'sender')
            
        return transfer
    
    def _complete_transfer(self, transfer):
        """Complete the transfer on blockchain when both parties approve"""
        try:
            blockchain = BlockchainService(self.user)
            tx_hash, error = blockchain.execute_transfer(
                transfer.parcel.land_id,
                transfer.sender.blockchain_address,
                transfer.recipient.blockchain_address,
                transfer.contract_hash or ""
            )
            
            if tx_hash:
                transfer.transaction_hash = tx_hash
                # Update parcel ownership in local database
                transfer.parcel.owner = transfer.recipient
                transfer.parcel.owner_address = transfer.recipient.blockchain_address
                transfer.parcel.save()
                
                logger.info(f"Transfer completed successfully: {tx_hash}")
            else:
                logger.error(f"Blockchain transfer failed: {error}")
                raise ValidationError(f"Blockchain transfer failed: {error}")
            
        except Exception as e:
            logger.error(f"Blockchain completion failed: {e}")
            raise ValidationError(f"Blockchain transaction failed: {e}")
    
    def _create_transfer_history(self, transfer, notes):
        """Create transfer history record"""
        try:
            # Check if TransferHistory model exists and create record
            TransferHistory = None
            try:
                TransferHistory = apps.get_model('registration', 'TransferHistory')
            except LookupError:
                logger.warning("TransferHistory model not found, skipping history creation")
                return
                
            if TransferHistory:
                TransferHistory.objects.create(
                    transfer=transfer,
                    from_user=transfer.sender,
                    to_user=transfer.recipient,
                    parcel=transfer.parcel,
                    status=transfer.status,
                    notes=notes
                )
        except Exception as e:
            logger.error(f"Failed to create transfer history: {e}")
    
    def _send_approval_notification(self, transfer, approver_type):
        """Send notification about approval"""
        try:
            if approver_type == 'sender':
                recipient_user = transfer.recipient
                subject = f"Sender Approved Transfer - Parcel {transfer.parcel.land_id}"
            else:
                recipient_user = transfer.sender
                subject = f"Recipient Approved Transfer - Parcel {transfer.parcel.land_id}"
            
            context = {
                'transfer': transfer,
                'approver_type': approver_type,
                'recipient_user': recipient_user,
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
            }
            
            # Try to render template, fallback to plain text
            try:
                message = render_to_string('emails/approval_notification.html', context)
            except:
                message = f"""
                The {approver_type} has approved the transfer for parcel {transfer.parcel.land_id}.
                
                Please log in to view the details.
                """
            
            send_mail(
                subject,
                message.strip(),
                settings.DEFAULT_FROM_EMAIL,
                [recipient_user.email],
                html_message=message if message != message.strip() else None,
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")

class AcceptTransferForm(forms.ModelForm):
    confirm_approval = forms.BooleanField(
        required=True,
        label="I confirm I accept this land transfer as the recipient"
    )
    
    approval_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Optional acceptance notes...'
        }),
        label="Acceptance Notes"
    )

    class Meta:
        model = Transfer
        fields = []

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance or not self.instance.pk:
            raise ValidationError("Invalid transfer request")
        
        if self.user != self.instance.recipient:
            raise ValidationError("Only the recipient can accept this transfer")
        
        valid_statuses = [Transfer.PENDING, Transfer.SENDER_APPROVED]
        if self.instance.status not in valid_statuses:
            raise ValidationError("This transfer cannot be accepted at this time")
        
        if self.instance.recipient_approved:
            raise ValidationError("You have already accepted this transfer")
        
        if not cleaned_data.get('confirm_approval'):
            raise ValidationError("You must confirm your acceptance")
        
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.recipient_approved = True
        transfer.recipient_approved_at = timezone.now()
        
        # Update status based on sender's approval status
        if transfer.sender_approved:
            transfer.status = Transfer.COMPLETED
            self._complete_transfer(transfer)
        else:
            transfer.status = Transfer.RECIPIENT_APPROVED
        
        if commit:
            transfer.save()
            self._create_transfer_history(transfer, "Recipient accepted transfer")
            self._send_approval_notification(transfer, 'recipient')
            
        return transfer
    
    def _complete_transfer(self, transfer):
        """Complete the transfer on blockchain when both parties approve"""
        try:
            blockchain = BlockchainService(self.user)
            tx_hash, error = blockchain.execute_transfer(
                transfer.parcel.land_id,
                transfer.sender.blockchain_address,
                transfer.recipient.blockchain_address,
                transfer.contract_hash or ""
            )
            
            if tx_hash:
                transfer.transaction_hash = tx_hash
                # Update parcel ownership in local database
                transfer.parcel.owner = transfer.recipient
                transfer.parcel.owner_address = transfer.recipient.blockchain_address
                transfer.parcel.save()
                
                logger.info(f"Transfer completed successfully: {tx_hash}")
            else:
                logger.error(f"Blockchain transfer failed: {error}")
                raise ValidationError(f"Blockchain transfer failed: {error}")
            
        except Exception as e:
            logger.error(f"Blockchain completion failed: {e}")
            raise ValidationError(f"Blockchain transaction failed: {e}")
    
    def _create_transfer_history(self, transfer, notes):
        """Create transfer history record"""
        try:
            # Check if TransferHistory model exists and create record
            TransferHistory = None
            try:
                TransferHistory = apps.get_model('registration', 'TransferHistory')
            except LookupError:
                logger.warning("TransferHistory model not found, skipping history creation")
                return
                
            if TransferHistory:
                TransferHistory.objects.create(
                    transfer=transfer,
                    from_user=transfer.sender,
                    to_user=transfer.recipient,
                    parcel=transfer.parcel,
                    status=transfer.status,
                    notes=notes
                )
        except Exception as e:
            logger.error(f"Failed to create transfer history: {e}")

class CancelTransferForm(forms.ModelForm):
    cancellation_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Explain why you are cancelling this transfer...'
        }),
        label="Reason for Cancellation"
    )
    confirm_cancellation = forms.BooleanField(
        required=True,
        label="I confirm I want to cancel this transfer"
    )

    class Meta:
        model = Transfer
        fields = []

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance or not self.instance.pk:
            raise ValidationError("Invalid transfer request")
        
        valid_statuses = [Transfer.PENDING, Transfer.SENDER_APPROVED, Transfer.RECIPIENT_APPROVED]
        if self.instance.status not in valid_statuses:
            raise ValidationError("This transfer cannot be canceled")
        
        if self.user not in [self.instance.sender, self.instance.recipient]:
            raise ValidationError("You are not authorized to cancel this transfer")
        
        if not cleaned_data.get('confirm_cancellation'):
            raise ValidationError("You must confirm cancellation")
        
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.status = Transfer.CANCELLED
        transfer.cancellation_reason = self.cleaned_data['cancellation_reason']
        transfer.cancelled_at = timezone.now()
        
        if commit:
            transfer.save()
            try:
                blockchain = BlockchainService(self.user)
                # Use cancel_transfer method instead of reject_transfer
                tx_hash = blockchain.cancel_transfer(transfer.parcel.land_id)
                if tx_hash:
                    transfer.transaction_hash = tx_hash
                self._create_transfer_history(transfer, f"Cancelled by {self.user.username}")
            except Exception as e:
                logger.error(f"Blockchain cancellation failed: {e}")
                # Don't raise error - cancellation should still proceed locally
        return transfer
    
    def _create_transfer_history(self, transfer, notes):
        """Create transfer history record"""
        try:
            # Check if TransferHistory model exists and create record
            TransferHistory = None
            try:
                TransferHistory = apps.get_model('registration', 'TransferHistory')
            except LookupError:
                logger.warning("TransferHistory model not found, skipping history creation")
                return
                
            if TransferHistory:
                TransferHistory.objects.create(
                    transfer=transfer,
                    from_user=transfer.sender,
                    to_user=transfer.recipient,
                    parcel=transfer.parcel,
                    status=transfer.status,
                    notes=notes
                )
        except Exception as e:
            logger.error(f"Failed to create transfer history: {e}")

class RejectTransferForm(forms.ModelForm):
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Explain why you are rejecting this transfer...'
        }),
        label="Reason for Rejection"
    )
    confirm_rejection = forms.BooleanField(
        required=True,
        label="I confirm I want to reject this transfer"
    )

    class Meta:
        model = Transfer
        fields = []

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.instance or not self.instance.pk:
            raise ValidationError("Invalid transfer request")
        
        valid_statuses = [Transfer.PENDING, Transfer.SENDER_APPROVED, Transfer.RECIPIENT_APPROVED]
        if self.instance.status not in valid_statuses:
            raise ValidationError("This transfer cannot be rejected")
        
        if self.user != self.instance.recipient and not (self.user.is_staff or self.user.is_superuser):
            raise ValidationError("You are not authorized to reject this transfer")
        
        if not cleaned_data.get('confirm_rejection'):
            raise ValidationError("You must confirm rejection")
        
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.status = Transfer.REJECTED
        transfer.rejection_reason = self.cleaned_data['rejection_reason']
        transfer.rejected_at = timezone.now()
        
        if commit:
            transfer.save()
            try:
                blockchain = BlockchainService(self.user)
                # Use reject_transfer method
                tx_hash = blockchain.reject_transfer(transfer.parcel.land_id)
                if tx_hash:
                    transfer.transaction_hash = tx_hash
                self._create_transfer_history(transfer, f"Rejected by {self.user.username}")
            except Exception as e:
                logger.error(f"Blockchain rejection failed: {e}")
                # Don't raise error - rejection should still proceed locally
        return transfer
    
    def _create_transfer_history(self, transfer, notes):
        """Create transfer history record"""
        try:
            # Check if TransferHistory model exists and create record
            TransferHistory = None
            try:
                TransferHistory = apps.get_model('registration', 'TransferHistory')
            except LookupError:
                logger.warning("TransferHistory model not found, skipping history creation")
                return
                
            if TransferHistory:
                TransferHistory.objects.create(
                    transfer=transfer,
                    from_user=transfer.sender,
                    to_user=transfer.recipient,
                    parcel=transfer.parcel,
                    status=transfer.status,
                    notes=notes
                )
        except Exception as e:
            logger.error(f"Failed to create transfer history: {e}")

# Add a simple transfer form for direct transfers (without dual approval)
class DirectTransferForm(forms.ModelForm):
    recipient = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select the recipient user"
    )
    
    contract_file = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text="Optional transfer contract document"
    )

    class Meta:
        model = Transfer
        fields = ['parcel', 'recipient', 'terms']
        widgets = {
            'parcel': forms.Select(attrs={'class': 'form-select'}),
            'terms': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.is_admin = kwargs.pop('is_admin', False)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filter parcels and recipients
            if self.is_admin:
                parcels = Parcel.objects.all()
                recipients = User.objects.exclude(blockchain_address__isnull=True).exclude(blockchain_address='')
            else:
                parcels = Parcel.objects.filter(owner=self.user)
                recipients = User.objects.exclude(blockchain_address__isnull=True).exclude(blockchain_address='').exclude(id=self.user.id)
            
            self.fields['parcel'].queryset = parcels
            self.fields['recipient'].queryset = recipients

    def clean(self):
        cleaned_data = super().clean()
        parcel = cleaned_data.get('parcel')
        recipient = cleaned_data.get('recipient')
        
        if parcel and recipient:
            # Ownership validation
            if not self.is_admin and parcel.owner != self.user:
                raise ValidationError("You can only transfer parcels that you own")
            
            if not recipient.blockchain_address:
                raise ValidationError("Recipient must have a blockchain address")
                
        return cleaned_data

    def save(self, commit=True):
        transfer = super().save(commit=False)
        transfer.sender = self.user
        transfer.status = Transfer.PENDING
        
        # Handle contract file
        if 'contract_file' in self.files:
            file_service = FileHashService()
            contract_file = self.files['contract_file']
            ipfs_hash = file_service.add_file(contract_file)
            transfer.contract_hash = ipfs_hash
        
        if commit:
            transfer.save()
            
        return transfer