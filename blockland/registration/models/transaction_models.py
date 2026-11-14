from django.db import models
from django.utils import timezone
from .user_models import User  # Updated to match your custom user model
from .property_models import Property

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('PURCHASE', 'Property Purchase'),
        ('TRANSFER', 'Ownership Transfer'),
        ('FEE', 'Administrative Fee'),
    ]
    
    transaction_id = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')  # Updated to User
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    
    # CouchDB Integration (to match your user model pattern)
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    # Additional metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['blockchain_tx_hash']),
            models.Index(fields=['is_completed']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.transaction_id} - {self.get_transaction_type_display()}"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync transaction data to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            transaction_doc = {
                'type': 'transaction',
                'postgres_id': self.id,
                'transaction_id': self.transaction_id,
                'transaction_type': self.transaction_type,
                'user_id': self.user.id,
                'user_couchdb_id': self.user.couchdb_id,
                'user_blockchain_address': self.user.blockchain_address,
                'property_id': self.property.id if self.property else None,
                'amount': float(self.amount) if self.amount else None,
                'date': self.date.isoformat() if self.date else None,
                'blockchain_tx_hash': self.blockchain_tx_hash,
                'is_completed': self.is_completed,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                transaction_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    transaction_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(transaction_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing transaction to CouchDB: {e}")
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
                print(f"Error deleting transaction from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update a transaction from CouchDB document"""
        try:
            # Get user instance
            user_id = couchdb_doc.get('user_id')
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    print(f"User with ID {user_id} not found")
                    return None, False
            
            # Get property instance if exists
            property_id = couchdb_doc.get('property_id')
            property_obj = None
            if property_id:
                try:
                    property_obj = Property.objects.get(id=property_id)
                except Property.DoesNotExist:
                    print(f"Property with ID {property_id} not found")
            
            transaction, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'transaction_id': couchdb_doc.get('transaction_id'),
                    'transaction_type': couchdb_doc.get('transaction_type'),
                    'user': user,
                    'property': property_obj,
                    'amount': couchdb_doc.get('amount'),
                    'date': timezone.datetime.fromisoformat(couchdb_doc.get('date')) if couchdb_doc.get('date') else None,
                    'blockchain_tx_hash': couchdb_doc.get('blockchain_tx_hash'),
                    'is_completed': couchdb_doc.get('is_completed', False),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing transaction
                transaction.transaction_id = couchdb_doc.get('transaction_id', transaction.transaction_id)
                transaction.transaction_type = couchdb_doc.get('transaction_type', transaction.transaction_type)
                transaction.user = user or transaction.user
                transaction.property = property_obj or transaction.property
                transaction.amount = couchdb_doc.get('amount', transaction.amount)
                transaction.blockchain_tx_hash = couchdb_doc.get('blockchain_tx_hash', transaction.blockchain_tx_hash)
                transaction.is_completed = couchdb_doc.get('is_completed', transaction.is_completed)
                transaction.couchdb_id = couchdb_doc.get('_id', transaction.couchdb_id)
                transaction.couchdb_rev = couchdb_doc.get('_rev', transaction.couchdb_rev)
                transaction.save()
            
            return transaction, created
        except Exception as e:
            print(f"Error creating transaction from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        """Return absolute URL for the transaction"""
        from django.urls import reverse
        return reverse('transaction-detail', kwargs={'pk': self.pk})
