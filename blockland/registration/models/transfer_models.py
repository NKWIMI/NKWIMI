# # registration/models/transfer_models.py
# from django.db import models
# from django.utils import timezone
# from django.urls import reverse
# from django.core.exceptions import ValidationError
# from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes.models import ContentType
# from .user_models import User as User # Changed from User to User
# from .parcel_models import Parcel 

# class Transfer(models.Model):
#     """Model for property transfer between users with blockchain integration"""
#     PENDING = 'pending'
#     ACCEPTED = 'accepted'
#     REJECTED = 'rejected'
#     CANCELED = 'canceled'
#     EXPIRED = 'expired'
#     STATUS_CHOICES = [
#         (PENDING, 'Pending'),
#         (ACCEPTED, 'Accepted'),
#         (REJECTED, 'Rejected'),
#         (CANCELED, 'Canceled'),
#         (EXPIRED, 'Expired'),
#     ]

#     sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers')  # Changed to User
#     recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transfers')  # Changed to User
#     parcel = models.ForeignKey('Parcel', on_delete=models.CASCADE, related_name='transfers')  
    
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField(null=True, blank=True)
#     accepted_at = models.DateTimeField(null=True, blank=True)
#     rejected_at = models.DateTimeField(null=True, blank=True)
#     canceled_at = models.DateTimeField(null=True, blank=True)
#     expired_at = models.DateTimeField(null=True, blank=True)
#     cancellation_reason = models.TextField(blank=True, null=True)
#     rejection_reason = models.TextField(blank=True, null=True)
#     terms = models.TextField(blank=True, null=True)
#     contract_hash = models.CharField(max_length=66, blank=True, null=True)
#     transaction_hash = models.CharField(max_length=66, blank=True, null=True)
#     smart_contract_address = models.CharField(max_length=42, blank=True, null=True)
#     gas_used = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
#     block_number = models.PositiveIntegerField(null=True, blank=True)
    
#     # CouchDB integration fields
#     couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
#     couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
#     class Meta:
#         ordering = ['-created_at']
#         verbose_name = "Transfer"
#         verbose_name_plural = "Transfers"
#         indexes = [
#             models.Index(fields=['status']),
#             models.Index(fields=['parcel']),
#             models.Index(fields=['sender']),
#             models.Index(fields=['recipient']),
#             models.Index(fields=['expires_at']),
#             models.Index(fields=['couchdb_id']),
#         ]
#         constraints = [
#             models.CheckConstraint(
#                 check=models.Q(expires_at__gt=models.F('created_at')),
#                 name="expires_after_creation"
#             )
#         ]

#     def __str__(self):
#         return f"Transfer #{self.id} - {self.parcel} ({self.get_status_display()})"

#     def clean(self):
#         """Validate that parcel doesn't have active transfers"""
#         super().clean()
        
#         # Skip validation for existing transfers that are being updated
#         if self.pk:
#             return
            
#         # Check for active transfers for the same parcel
#         active_transfers = Transfer.objects.filter(
#             parcel=self.parcel,
#             status__in=[self.PENDING, self.ACCEPTED]
#         )
        
#         if active_transfers.exists():
#             raise ValidationError({
#                 'parcel': 'This parcel already has an active transfer. Please cancel the existing transfer first.'
#             })

#     def save(self, *args, **kwargs):
#         # Run validation
#         self.full_clean()
        
#         if not self.expires_at and self.status == self.PENDING:
#             self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
#         super().save(*args, **kwargs)
#         self.sync_to_couchdb()

#     def accept(self):
#         if self.status != self.PENDING:
#             raise ValueError("Only pending transfers can be accepted")
        
#         # Check for active transfers
#         active_transfers = Transfer.objects.filter(
#             parcel=self.parcel,
#             status__in=[self.PENDING, self.ACCEPTED]
#         ).exclude(pk=self.pk)
        
#         if active_transfers.exists():
#             raise ValueError("This parcel already has an active transfer")
            
#         self.status = self.ACCEPTED
#         self.accepted_at = timezone.now()
#         self.parcel.owner = self.recipient
#         self.parcel.save()
#         self.save()
#         self._create_transfer_history("Accepted")

#     def reject(self, reason=None):
#         if self.status != self.PENDING:
#             raise ValueError("Only pending transfers can be rejected")
#         self.status = self.REJECTED
#         self.rejected_at = timezone.now()
#         self.rejection_reason = reason
#         self.save()
#         self._create_transfer_history("Rejected")

#     def cancel(self, reason=None):
#         if self.status != self.PENDING:
#             raise ValueError("Only pending transfers can be canceled")
#         self.status = self.CANCELED
#         self.canceled_at = timezone.now()
#         self.cancellation_reason = reason
#         self.save()
#         self._create_transfer_history("Canceled")

#     def expire(self):
#         if self.status != self.PENDING:
#             raise ValueError("Only pending transfers can expire")
#         self.status = self.EXPIRED
#         self.expired_at = timezone.now()
#         self.save()
#         self._create_transfer_history("Expired")

#     def is_expired(self):
#         return (
#             self.status == self.PENDING and 
#             self.expires_at and 
#             timezone.now() > self.expires_at
#         )

#     def can_be_transferred(self):
#         """Check if this parcel can be transferred (no active transfers)"""
#         active_transfers = Transfer.objects.filter(
#             parcel=self.parcel,
#             status__in=[self.PENDING, self.ACCEPTED]
#         ).exclude(pk=self.pk)
        
#         return not active_transfers.exists()

#     def _create_transfer_history(self, action):
#         TransferHistory.objects.create(
#             transfer=self,
#             from_user=self.sender,
#             to_user=self.recipient,
#             parcel=self.parcel,
#             status=self.status,
#             transaction_hash=self.transaction_hash or '',
#             notes=f"Transfer {action.lower()}"
#         )

#     def sync_to_couchdb(self):
#         """Sync transfer data to CouchDB"""
#         from .utils import get_couchdb_connection
#         db = get_couchdb_connection()
#         if db:
#             transfer_doc = {
#                 'type': 'transfer',
#                 'postgres_id': self.id,
#                 'sender_id': self.sender_id,
#                 'recipient_id': self.recipient_id,
#                 'parcel_id': self.parcel_id,
#                 'status': self.status,
#                 'created_at': self.created_at.isoformat() if self.created_at else None,
#                 'expires_at': self.expires_at.isoformat() if self.expires_at else None,
#                 'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
#                 'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
#                 'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
#                 'expired_at': self.expired_at.isoformat() if self.expired_at else None,
#                 'cancellation_reason': self.cancellation_reason,
#                 'rejection_reason': self.rejection_reason,
#                 'terms': self.terms,
#                 'contract_hash': self.contract_hash,
#                 'transaction_hash': self.transaction_hash,
#                 'smart_contract_address': self.smart_contract_address,
#                 'gas_used': str(self.gas_used) if self.gas_used else None,
#                 'block_number': self.block_number
#             }

#             # If we already have a CouchDB ID, include it for update
#             if self.couchdb_id:
#                 transfer_doc['_id'] = self.couchdb_id
#                 if self.couchdb_rev:
#                     transfer_doc['_rev'] = self.couchdb_rev

#             try:
#                 doc_id, doc_rev = db.save(transfer_doc)
#                 self.couchdb_id = doc_id
#                 self.couchdb_rev = doc_rev
#                 # Save again to store the CouchDB metadata, but avoid infinite recursion
#                 super().save(update_fields=['couchdb_id', 'couchdb_rev'])
#                 return True
#             except Exception as e:
#                 print(f"Error syncing transfer to CouchDB: {e}")
#                 return False
#         return False

#     def delete(self, *args, **kwargs):
#         """Override delete to also remove from CouchDB"""
#         from .utils import get_couchdb_connection
#         db = get_couchdb_connection()
#         if db and self.couchdb_id:
#             try:
#                 doc = db[self.couchdb_id]
#                 db.delete(doc)
#             except Exception as e:
#                 print(f"Error deleting transfer from CouchDB: {e}")
        
#         super().delete(*args, **kwargs)

#     def get_absolute_url(self):
#         return reverse('transfer:transfer_detail', kwargs={'pk': self.pk})

# class TransferHistory(models.Model):
#     """Historical record of all property transfers"""
#     transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name='history')
#     from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_transfer_history')  # Changed to User
#     to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_transfer_history')  # Changed to User
#     parcel = models.ForeignKey('Parcel', on_delete=models.SET_NULL, null=True) 
#     status = models.CharField(max_length=20)
#     timestamp = models.DateTimeField(auto_now_add=True)
#     transaction_hash = models.CharField(max_length=66, blank=True, null=True)
#     notes = models.TextField(blank=True)

#     # CouchDB integration fields
#     couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
#     couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

#     class Meta:
#         verbose_name = "Transfer History"
#         verbose_name_plural = "Transfer Histories"
#         ordering = ['-timestamp']
#         indexes = [
#             models.Index(fields=['transfer']),
#             models.Index(fields=['from_user']),
#             models.Index(fields=['to_user']),
#             models.Index(fields=['couchdb_id']),
#         ]

#     def save(self, *args, **kwargs):
#         # If this is a new history record and we have a transfer with transaction hash
#         if not self.pk and self.transfer and self.transfer.transaction_hash:
#             self.transaction_hash = self.transfer.transaction_hash
        
#         super().save(*args, **kwargs)
#         self.sync_to_couchdb()

#     def sync_to_couchdb(self):
#         """Sync transfer history to CouchDB"""
#         from .utils import get_couchdb_connection
#         db = get_couchdb_connection()
#         if db:
#             history_doc = {
#                 'type': 'transfer_history',
#                 'postgres_id': self.id,
#                 'transfer_id': self.transfer_id,
#                 'from_user_id': self.from_user_id,
#                 'to_user_id': self.to_user_id,
#                 'parcel_id': self.parcel_id,
#                 'status': self.status,
#                 'timestamp': self.timestamp.isoformat() if self.timestamp else None,
#                 'transaction_hash': self.transaction_hash,
#                 'notes': self.notes
#             }

#             if self.couchdb_id:
#                 history_doc['_id'] = self.couchdb_id
#                 if self.couchdb_rev:
#                     history_doc['_rev'] = self.couchdb_rev

#             try:
#                 doc_id, doc_rev = db.save(history_doc)
#                 self.couchdb_id = doc_id
#                 self.couchdb_rev = doc_rev
#                 super().save(update_fields=['couchdb_id', 'couchdb_rev'])
#                 return True
#             except Exception as e:
#                 print(f"Error syncing transfer history to CouchDB: {e}")
#                 return False
#         return False

#     def __str__(self):
#         return f"Transfer #{self.transfer.id} history"

# class PendingTransfer(models.Model):
#     """Model for tracking pending transfers before blockchain confirmation"""
#     transfer = models.OneToOneField(Transfer, on_delete=models.CASCADE, primary_key=True, related_name='pending_details')
#     created_at = models.DateTimeField(auto_now_add=True)
#     last_checked = models.DateTimeField(auto_now=True)
#     confirmation_attempts = models.PositiveIntegerField(default=0)
#     blockchain_tx_id = models.CharField(max_length=100, blank=True, null=True)
#     is_confirmed = models.BooleanField(default=False)

#     # CouchDB integration fields
#     couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
#     couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

#     class Meta:
#         verbose_name = "Pending Transfer"
#         verbose_name_plural = "Pending Transfers"
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['couchdb_id']),
#         ]

#     def __str__(self):
#         return f"Pending transfer #{self.transfer.id}"

#     def save(self, *args, **kwargs):
#         super().save(*args, **kwargs)
#         self.sync_to_couchdb()

#     def sync_to_couchdb(self):
#         """Sync pending transfer to CouchDB"""
#         from .utils import get_couchdb_connection
#         db = get_couchdb_connection()
#         if db:
#             pending_doc = {
#                 'type': 'pending_transfer',
#                 'postgres_id': self.transfer_id,  # Using transfer_id as primary key
#                 'transfer_id': self.transfer_id,
#                 'created_at': self.created_at.isoformat() if self.created_at else None,
#                 'last_checked': self.last_checked.isoformat() if self.last_checked else None,
#                 'confirmation_attempts': self.confirmation_attempts,
#                 'blockchain_tx_id': self.blockchain_tx_id,
#                 'is_confirmed': self.is_confirmed
#             }

#             if self.couchdb_id:
#                 pending_doc['_id'] = self.couchdb_id
#                 if self.couchdb_rev:
#                     pending_doc['_rev'] = self.couchdb_rev

#             try:
#                 doc_id, doc_rev = db.save(pending_doc)
#                 self.couchdb_id = doc_id
#                 self.couchdb_rev = doc_rev
#                 super().save(update_fields=['couchdb_id', 'couchdb_rev'])
#                 return True
#             except Exception as e:
#                 print(f"Error syncing pending transfer to CouchDB: {e}")
#                 return False
#         return False


# registration/models/transfer_models.py
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .user_models import User
from .parcel_models import Parcel

class Transfer(models.Model):
    PENDING = 'pending'           # Transfer created, waiting for sender approval
    SENDER_APPROVED = 'sender_approved'  # Sender approved, waiting for recipient
    RECIPIENT_APPROVED = 'recipient_approved'  # Recipient approved, waiting for sender
    COMPLETED = 'completed'       # Both approved, transfer executed
    CANCELED = 'canceled'
    REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending Sender Approval'),
        (SENDER_APPROVED, 'Sender Approved - Waiting Recipient'),
        (RECIPIENT_APPROVED, 'Recipient Approved - Waiting Sender'),
        (COMPLETED, 'Completed'),
        (CANCELED, 'Canceled'),
        (REJECTED, 'Rejected'),
    ]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_transfers')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_transfers')
    parcel = models.ForeignKey('Parcel', on_delete=models.CASCADE, related_name='transfers')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    
    # Dual approval tracking
    sender_approved = models.BooleanField(default=False)
    recipient_approved = models.BooleanField(default=False)
    sender_approved_at = models.DateTimeField(null=True, blank=True)
    recipient_approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    
    cancellation_reason = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    terms = models.TextField(blank=True, null=True)
    contract_hash = models.CharField(max_length=66, blank=True, null=True)
    transaction_hash = models.CharField(max_length=66, blank=True, null=True)
    smart_contract_address = models.CharField(max_length=42, blank=True, null=True)
    gas_used = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)
    
    # CouchDB integration fields
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['parcel']),
            models.Index(fields=['sender']),
            models.Index(fields=['recipient']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['sender_approved']),
            models.Index(fields=['recipient_approved']),
            models.Index(fields=['couchdb_id']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(expires_at__gt=models.F('created_at')),
                name="expires_after_creation"
            )
        ]

    def __str__(self):
        return f"Transfer #{self.id} - {self.parcel} ({self.get_status_display()})"

    def clean(self):
        """Validate that parcel doesn't have active transfers"""
        super().clean()
        
        # Skip validation for existing transfers that are being updated
        if self.pk:
            return
            
        # Check for active transfers for the same parcel
        active_transfers = Transfer.objects.filter(
            parcel=self.parcel,
            status__in=[self.PENDING, self.SENDER_APPROVED, self.RECIPIENT_APPROVED, self.COMPLETED]
        )
        
        if active_transfers.exists():
            raise ValidationError({
                'parcel': 'This parcel already has an active transfer. Please cancel the existing transfer first.'
            })

    def save(self, *args, **kwargs):
        # Run validation
        self.full_clean()
        
        # Set expiration date for pending transfers
        if not self.expires_at and self.status == self.PENDING:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
        # Auto-complete if both parties approve
        if self.sender_approved and self.recipient_approved and self.status != self.COMPLETED:
            self.status = self.COMPLETED
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def approve_by_sender(self):
        """Approve transfer by sender"""
        if self.status not in [self.PENDING, self.RECIPIENT_APPROVED]:
            raise ValueError("Transfer cannot be approved by sender at this time")
        
        if self.sender_approved:
            raise ValueError("Sender has already approved this transfer")
        
        self.sender_approved = True
        self.sender_approved_at = timezone.now()
        
        if self.recipient_approved:
            self.status = self.COMPLETED
            self.completed_at = timezone.now()
        else:
            self.status = self.SENDER_APPROVED
        
        self.save()
        self._create_transfer_history("Approved by sender")

    def approve_by_recipient(self):
        """Approve transfer by recipient"""
        if self.status not in [self.PENDING, self.SENDER_APPROVED]:
            raise ValueError("Transfer cannot be approved by recipient at this time")
        
        if self.recipient_approved:
            raise ValueError("Recipient has already approved this transfer")
        
        self.recipient_approved = True
        self.recipient_approved_at = timezone.now()
        
        if self.sender_approved:
            self.status = self.COMPLETED
            self.completed_at = timezone.now()
        else:
            self.status = self.RECIPIENT_APPROVED
        
        self.save()
        self._create_transfer_history("Approved by recipient")

    def complete_transfer(self, user):
        """Complete the transfer on blockchain (called when both parties approve)"""
        if self.status != self.COMPLETED:
            raise ValueError("Transfer must be completed before blockchain execution")
        
        try:
            blockchain = BlockchainService(user)
            tx_hash = blockchain.complete_transfer(
                self.parcel.land_id,
                self.recipient.blockchain_address,
                self.contract_hash
            )
            self.transaction_hash = tx_hash
            self.parcel.owner = self.recipient
            self.parcel.save()
            self.save()
            self._create_transfer_history("Completed on blockchain")
        except Exception as e:
            logger.error(f"Blockchain completion failed: {e}")
            raise

    def reject(self, reason=None, rejected_by=None):
        """Reject the transfer"""
        if self.status not in [self.PENDING, self.SENDER_APPROVED, self.RECIPIENT_APPROVED]:
            raise ValueError("Transfer cannot be rejected at this time")
        
        self.status = self.REJECTED
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        
        rejected_by_name = rejected_by.username if rejected_by else "System"
        self._create_transfer_history(f"Rejected by {rejected_by_name}")

    def cancel(self, reason=None, canceled_by=None):
        """Cancel the transfer"""
        if self.status not in [self.PENDING, self.SENDER_APPROVED, self.RECIPIENT_APPROVED]:
            raise ValueError("Transfer cannot be canceled at this time")
        
        self.status = self.CANCELED
        self.canceled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()
        
        canceled_by_name = canceled_by.username if canceled_by else "System"
        self._create_transfer_history(f"Canceled by {canceled_by_name}")

    def expire(self):
        """Mark transfer as expired"""
        if self.status != self.PENDING:
            raise ValueError("Only pending transfers can expire")
        
        self.status = self.EXPIRED
        self.expired_at = timezone.now()
        self.save()
        self._create_transfer_history("Expired")

    def is_expired(self):
        """Check if transfer has expired"""
        return (
            self.status in [self.PENDING, self.SENDER_APPROVED, self.RECIPIENT_APPROVED] and 
            self.expires_at and 
            timezone.now() > self.expires_at
        )

    def can_be_approved_by(self, user):
        """Check if user can approve this transfer"""
        if user == self.sender:
            return not self.sender_approved and self.status in [self.PENDING, self.RECIPIENT_APPROVED]
        elif user == self.recipient:
            return not self.recipient_approved and self.status in [self.PENDING, self.SENDER_APPROVED]
        return False

    def can_be_canceled_by(self, user):
        """Check if user can cancel this transfer"""
        if user in [self.sender, self.recipient]:
            return self.status in [self.PENDING, self.SENDER_APPROVED, self.RECIPIENT_APPROVED]
        return False

    def get_approval_status(self):
        """Get human-readable approval status"""
        if self.sender_approved and self.recipient_approved:
            return "Both parties approved"
        elif self.sender_approved:
            return "Awaiting recipient approval"
        elif self.recipient_approved:
            return "Awaiting sender approval"
        else:
            return "Awaiting both approvals"

    def _create_transfer_history(self, action):
        """Create transfer history record"""
        TransferHistory.objects.create(
            transfer=self,
            from_user=self.sender,
            to_user=self.recipient,
            parcel=self.parcel,
            status=self.status,
            transaction_hash=self.transaction_hash or '',
            notes=f"Transfer {action}"
        )

    def sync_to_couchdb(self):
        """Sync transfer data to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            transfer_doc = {
                'type': 'transfer',
                'postgres_id': self.id,
                'sender_id': self.sender_id,
                'recipient_id': self.recipient_id,
                'parcel_id': self.parcel_id,
                'status': self.status,
                'sender_approved': self.sender_approved,
                'recipient_approved': self.recipient_approved,
                'sender_approved_at': self.sender_approved_at.isoformat() if self.sender_approved_at else None,
                'recipient_approved_at': self.recipient_approved_at.isoformat() if self.recipient_approved_at else None,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'expires_at': self.expires_at.isoformat() if self.expires_at else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
                'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
                'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
                'expired_at': self.expired_at.isoformat() if self.expired_at else None,
                'cancellation_reason': self.cancellation_reason,
                'rejection_reason': self.rejection_reason,
                'terms': self.terms,
                'contract_hash': self.contract_hash,
                'transaction_hash': self.transaction_hash,
                'smart_contract_address': self.smart_contract_address,
                'gas_used': str(self.gas_used) if self.gas_used else None,
                'block_number': self.block_number,
                'approval_status': self.get_approval_status()
            }

            if self.couchdb_id:
                transfer_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    transfer_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(transfer_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing transfer to CouchDB: {e}")
                return False
        return False

    def delete(self, *args, **kwargs):
        """Override delete to also remove from CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db and self.couchdb_id:
            try:
                doc = db[self.couchdb_id]
                db.delete(doc)
            except Exception as e:
                print(f"Error deleting transfer from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('transfer:transfer_detail', kwargs={'pk': self.pk})

# Keep the existing TransferHistory, PendingTransfer classes as they are...
class TransferHistory(models.Model):
    """Historical record of all property transfers"""
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE, related_name='history')
    from_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_transfer_history')
    to_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_transfer_history')
    parcel = models.ForeignKey('Parcel', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_hash = models.CharField(max_length=66, blank=True, null=True)
    notes = models.TextField(blank=True)

    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        verbose_name = "Transfer History"
        verbose_name_plural = "Transfer Histories"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transfer']),
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
            models.Index(fields=['couchdb_id']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk and self.transfer and self.transfer.transaction_hash:
            self.transaction_hash = self.transfer.transaction_hash
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            history_doc = {
                'type': 'transfer_history',
                'postgres_id': self.id,
                'transfer_id': self.transfer_id,
                'from_user_id': self.from_user_id,
                'to_user_id': self.to_user_id,
                'parcel_id': self.parcel_id,
                'status': self.status,
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'transaction_hash': self.transaction_hash,
                'notes': self.notes
            }

            if self.couchdb_id:
                history_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    history_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(history_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing transfer history to CouchDB: {e}")
                return False
        return False

    def __str__(self):
        return f"Transfer #{self.transfer.id} history"

class PendingTransfer(models.Model):
    """Model for tracking pending transfers before blockchain confirmation"""
    transfer = models.OneToOneField(Transfer, on_delete=models.CASCADE, primary_key=True, related_name='pending_details')
    created_at = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(auto_now=True)
    confirmation_attempts = models.PositiveIntegerField(default=0)
    blockchain_tx_id = models.CharField(max_length=100, blank=True, null=True)
    is_confirmed = models.BooleanField(default=False)

    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        verbose_name = "Pending Transfer"
        verbose_name_plural = "Pending Transfers"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"Pending transfer #{self.transfer.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            pending_doc = {
                'type': 'pending_transfer',
                'postgres_id': self.transfer_id,
                'transfer_id': self.transfer_id,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'last_checked': self.last_checked.isoformat() if self.last_checked else None,
                'confirmation_attempts': self.confirmation_attempts,
                'blockchain_tx_id': self.blockchain_tx_id,
                'is_confirmed': self.is_confirmed
            }

            if self.couchdb_id:
                pending_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    pending_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(pending_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing pending transfer to CouchDB: {e}")
                return False
        return False