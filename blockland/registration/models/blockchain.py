# registration/models/blockchain.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

class Block(models.Model):
    hash = models.CharField(max_length=64, unique=True)
    height = models.IntegerField(unique=True)
    timestamp = models.DateTimeField()
    previous_hash = models.CharField(max_length=64)
    miner = models.CharField(max_length=42, blank=True, null=True)
    difficulty = models.DecimalField(max_digits=20, decimal_places=2)
    nonce = models.BigIntegerField()
    
    # Add the missing fields from CouchDB
    type = models.CharField(max_length=20, default='block')  # Added type field
    reward = models.DecimalField(max_digits=20, decimal_places=8, default=0, null=True, blank=True)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=0, null=True, blank=True)
    
    # New gas-related fields
    gas_used = models.BigIntegerField(null=True, blank=True)
    gas_limit = models.BigIntegerField(null=True, blank=True)
    
    # Django timestamps (to match CouchDB)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    class Meta:
        ordering = ['-height']
        verbose_name = 'Blockchain Block'
        verbose_name_plural = 'Blockchain Blocks'
        indexes = [
            models.Index(fields=['hash']),
            models.Index(fields=['height']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['couchdb_id']),
        ]
        
    def __str__(self):
        return f"Block #{self.height} ({self.hash[:10]}...)"

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update block from CouchDB document"""
        try:
            timestamp = couchdb_doc.get('timestamp')
            if timestamp:
                timestamp = timezone.datetime.fromisoformat(timestamp)

            created_at = couchdb_doc.get('created_at')
            if created_at:
                created_at = timezone.datetime.fromisoformat(created_at)

            updated_at = couchdb_doc.get('updated_at')
            if updated_at:
                updated_at = timezone.datetime.fromisoformat(updated_at)

            block, created = cls.objects.get_or_create(
                id=couchdb_doc.get('django_id'),  # Use django_id as the primary key
                defaults={
                    'hash': couchdb_doc.get('hash', ''),
                    'height': couchdb_doc.get('height', 0),
                    'timestamp': timestamp,
                    'previous_hash': couchdb_doc.get('previous_hash', ''),
                    'miner': couchdb_doc.get('miner', ''),
                    'difficulty': couchdb_doc.get('difficulty', 0),
                    'nonce': couchdb_doc.get('nonce', 0),
                    'type': couchdb_doc.get('type', 'block'),  # Added type
                    'reward': couchdb_doc.get('reward', 0),
                    'fee': couchdb_doc.get('fee', 0),
                    'gas_used': couchdb_doc.get('gas_used'),
                    'gas_limit': couchdb_doc.get('gas_limit'),
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing block
                block.hash = couchdb_doc.get('hash', block.hash)
                block.height = couchdb_doc.get('height', block.height)
                block.timestamp = timestamp or block.timestamp
                block.previous_hash = couchdb_doc.get('previous_hash', block.previous_hash)
                block.miner = couchdb_doc.get('miner', block.miner)
                block.difficulty = couchdb_doc.get('difficulty', block.difficulty)
                block.nonce = couchdb_doc.get('nonce', block.nonce)
                block.type = couchdb_doc.get('type', block.type)  # Added type
                block.reward = couchdb_doc.get('reward', block.reward)
                block.fee = couchdb_doc.get('fee', block.fee)
                block.gas_used = couchdb_doc.get('gas_used', block.gas_used)
                block.gas_limit = couchdb_doc.get('gas_limit', block.gas_limit)
                block.created_at = created_at or block.created_at
                block.updated_at = updated_at or block.updated_at
                block.couchdb_id = couchdb_doc.get('_id', block.couchdb_id)
                block.couchdb_rev = couchdb_doc.get('_rev', block.couchdb_rev)
                block.save()
            
            return block, created
        except Exception as e:
            print(f"Error creating block from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('block_detail', kwargs={'pk': self.pk})

    @property
    def short_hash(self):
        """Return truncated hash for display"""
        return f"{self.hash[:8]}...{self.hash[-4:]}" if self.hash else ""

class BlockchainTransaction(models.Model):
    tx_hash = models.CharField(max_length=64, unique=True)
    block = models.ForeignKey(
        Block, 
        on_delete=models.CASCADE, 
        related_name='blockchain_transactions'
    )
    sender = models.CharField(max_length=42)
    recipient = models.CharField(max_length=42)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    timestamp = models.DateTimeField()
    fee = models.DecimalField(max_digits=10, decimal_places=8)
    status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Blockchain Transaction'
        verbose_name_plural = 'Blockchain Transactions'
        indexes = [
            models.Index(fields=['tx_hash']),
            models.Index(fields=['sender']),
            models.Index(fields=['recipient']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['couchdb_id']),
        ]
        
    def __str__(self):
        return f"Blockchain TX {self.tx_hash[:10]}... ({self.amount} coins)"

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update transaction from CouchDB document"""
        try:
            # Get block instance
            block_id = couchdb_doc.get('block_id')
            block = None
            if block_id:
                try:
                    block = Block.objects.get(id=block_id)
                except Block.DoesNotExist:
                    print(f"Block with ID {block_id} not found")
                    return None, False

            timestamp = couchdb_doc.get('timestamp')
            if timestamp:
                timestamp = timezone.datetime.fromisoformat(timestamp)

            transaction, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'tx_hash': couchdb_doc.get('tx_hash', ''),
                    'block': block,
                    'sender': couchdb_doc.get('sender', ''),
                    'recipient': couchdb_doc.get('recipient', ''),
                    'amount': couchdb_doc.get('amount', 0),
                    'timestamp': timestamp,
                    'fee': couchdb_doc.get('fee', 0),
                    'status': couchdb_doc.get('status', 'pending'),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing transaction
                transaction.tx_hash = couchdb_doc.get('tx_hash', transaction.tx_hash)
                transaction.block = block or transaction.block
                transaction.sender = couchdb_doc.get('sender', transaction.sender)
                transaction.recipient = couchdb_doc.get('recipient', transaction.recipient)
                transaction.amount = couchdb_doc.get('amount', transaction.amount)
                transaction.timestamp = timestamp or transaction.timestamp
                transaction.fee = couchdb_doc.get('fee', transaction.fee)
                transaction.status = couchdb_doc.get('status', transaction.status)
                transaction.couchdb_id = couchdb_doc.get('_id', transaction.couchdb_id)
                transaction.couchdb_rev = couchdb_doc.get('_rev', transaction.couchdb_rev)
                transaction.save()
            
            return transaction, created
        except Exception as e:
            print(f"Error creating transaction from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('transaction_detail', kwargs={'pk': self.pk})

    @property
    def short_tx_hash(self):
        """Return truncated transaction hash for display"""
        return f"{self.tx_hash[:8]}...{self.tx_hash[-4:]}" if self.tx_hash else ""

    @property
    def short_sender(self):
        """Return truncated sender address for display"""
        return f"{self.sender[:8]}...{self.sender[-4:]}" if self.sender else ""

    @property
    def short_recipient(self):
        """Return truncated recipient address for display"""
        return f"{self.recipient[:8]}...{self.recipient[-4:]}" if self.recipient else ""