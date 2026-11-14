import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.urls import reverse
from .utils import validate_ethereum_address, get_encryption_key, generate_file_hash
from eth_account import Account
from cryptography.fernet import Fernet
import couchdb
from django.conf import settings
import hashlib

class User(AbstractUser):
    """Custom user model with CouchDB integration and all profile fields"""
    
    # Personal Information
    profile_picture = models.ImageField(
        upload_to='profile_pics/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Enter a valid phone number (e.g. +1234567890)"
            )
        ]
    )
    
    address_text = models.TextField(blank=True, null=True)
    
    # Identity Verification
    identity_document = models.FileField(
        upload_to='identity_docs/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        blank=True,
        null=True
    )
    
    identity_document_hash = models.CharField(max_length=255, blank=True, null=True, editable=False)
    is_identity_verified = models.BooleanField(default=False)
    
    # Blockchain Integration
    blockchain_address = models.CharField(
        max_length=42,
        blank=True,
        null=True,
        validators=[validate_ethereum_address],
        unique=True
    )
    
    encrypted_private_key = models.TextField(blank=True, null=True, editable=False)
    document_ipfs_hash = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    # Verification fields
    is_verified = models.BooleanField(default=False)  # FIXED: Changed Booleanfield to BooleanField
    verification_date = models.DateTimeField(null=True, blank=True)
    last_verification_check = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom related names to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='couchdb_user_set',
        related_query_name='couchdb_user',
        blank=True,
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='couchdb_user_set',
        related_query_name='couchdb_user',
        blank=True,
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['blockchain_address']),
            models.Index(fields=['is_identity_verified']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.username} ({self.blockchain_address or 'no wallet'})"

    def save(self, *args, **kwargs):
        # Generate blockchain credentials if missing
        if not self.blockchain_address or not self.encrypted_private_key:
            self._assign_ganache_wallet()
            
        # Generate file hash if identity document is uploaded
        if self.identity_document and not self.identity_document_hash:
            self.identity_document_hash = generate_file_hash(self.identity_document)
            
        # Save to PostgreSQL first
        super().save(*args, **kwargs)
        
        # Sync to CouchDB after saving to PostgreSQL
        self.sync_to_couchdb()

    def _assign_ganache_wallet(self):
        """Assign a Ganache test wallet to the user with fallback options"""
        if self.blockchain_address and self.encrypted_private_key:
            return False  # Already has a wallet
            
        # Extended Ganache private keys - add more as needed
        ganache_private_keys = [
            # Your original 10 wallets
            "f90e3cccb238919df5605f517812ddb7880a5ca6dc975925ce0bee7c365e149c",
            "2ccdc0ead622bbc094f07837dc5af613adecb800392fbed3fbdc2a10e2d20aac",
            "c5b184c316efb59d234fdb79ef130d92470cd6b6c558945244d740e0de53e7b6",
            "c31182bdc42cdff1510794a646f21ffde361f63f04024851f2cc8d065248a5a6",
            "b337905be04107bfe8bda5f53ecfe364cd93665eaf8a231a7d4bbca8be874d1a",
            "84b823393d69ab53a293ca08f80d5e8ca6037be4216cf420d874befcb7a42ad3",
            "ef76a8c2711279e9ea3f10cdc5be54a818c535f2cf862f0f9f98a0c4dad236a2",
            "26c5a0111fe286bfa87ed53bb0bc4acc079aab2f6358fc1f644a02728a421865",
            "22428b022114b904e5554eb81ad2c9257a30db1f664a1d85661618442bad3e40",
            "a9ed22570af2c8e0fabec1972dc6fd647a81d2a1548ce68eb3cf8910355c7548",
            # Add more private keys here as you get them from Ganache GUI
        ]
        
        # Get all currently used addresses
        used_addresses = set(User.objects.exclude(
            blockchain_address__isnull=True
        ).exclude(
            blockchain_address=''
        ).values_list('blockchain_address', flat=True))
        
        # If this user already has an address, remove it from used addresses
        if self.blockchain_address:
            used_addresses.discard(self.blockchain_address)
        
        print(f"🔍 Looking for available wallet for {self.username}...")
        print(f"   Currently used addresses: {len(used_addresses)}")
        print(f"   Available wallets in pool: {len(ganache_private_keys)}")
        
        # Try to assign from Ganache wallets first
        for private_key in ganache_private_keys:
            account = Account.from_key(private_key)
            if account.address.lower() not in [addr.lower() for addr in used_addresses]:
                # Found an available wallet!
                self.blockchain_address = account.address
                self._encrypt_private_key(private_key)
                print(f"✅ Assigned Ganache wallet to {self.username}: {account.address}")
                
                # Auto-fund in development
                if settings.DEBUG:
                    self._auto_fund_account()
                return True
        
        # Fallback: Create a new wallet if no Ganache wallets available
        print(f"⚠ No Ganache wallets available for {self.username}, creating new wallet...")
        return self._create_fallback_wallet()

    def _create_fallback_wallet(self):
        """Create a new wallet when Ganache wallets are exhausted"""
        try:
            # Create a new wallet
            account = Account.create()
            self.blockchain_address = account.address
            self._encrypt_private_key(account.key.hex())
            
            print(f"🆕 Created fallback wallet for {self.username}: {account.address}")
            print(f"⚠ NOTE: This wallet has no ETH and cannot make transactions")
            print(f"💡 Solution: Fund this address manually in Ganache GUI")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create fallback wallet: {e}")
            return False
    def _auto_fund_account(self):
        """Automatically fund new user accounts in development"""
        try:
            from registration.services.blockchain_service import BlockchainService
            blockchain = BlockchainService()
            
            # Check current balance
            balance = blockchain.w3.eth.get_balance(self.blockchain_address)
            balance_eth = blockchain.w3.from_wei(balance, 'ether')
            
            # Fund if balance is low
            if balance_eth < 1.0:
                print(f"💰 Auto-funding {self.username} with 2 ETH...")
                
                # Use the first Ganache account (usually has most ETH) as funder
                funder_private_key = os.getenv('FUNDER_PRIVATE_KEY', '')
                funder_account = Account.from_key(funder_private_key)
                
                # Build and send transaction
                tx_hash = blockchain.w3.eth.send_transaction({
                    'from': funder_account.address,
                    'to': self.blockchain_address,
                    'value': blockchain.w3.to_wei(2, 'ether'),
                    'gas': 21000,
                    'gasPrice': blockchain.w3.eth.gas_price
                })
                
                print(f"✅ Funded {self.username}: {tx_hash.hex()}")
                return True
                
        except Exception as e:
            print(f"❌ Auto-funding failed for {self.username}: {e}")
        return False

    def _encrypt_private_key(self, private_key):
        """Encrypt private key using Fernet symmetric encryption"""
        cipher_suite = Fernet(get_encryption_key())
        encrypted_key = cipher_suite.encrypt(private_key.encode()).decode()
        self.encrypted_private_key = encrypted_key

    def get_decrypted_private_key(self):
        """Decrypt and return the private key"""
        if not self.encrypted_private_key:
            return None
        cipher_suite = Fernet(get_encryption_key())
        return cipher_suite.decrypt(self.encrypted_private_key.encode()).decode()

    def has_complete_profile(self):
        """Check if profile has all required fields filled"""
        return all([
            self.phone_number,
            self.address_text,
            self.blockchain_address,
            self.identity_document
        ])

    def get_absolute_url(self):
        # FIXED: Use the correct URL pattern with namespace
        return reverse('profile:profile_detail', kwargs={'pk': self.pk})

    def sync_to_couchdb(self):
        """Sync user data to CouchDB"""
        from .utils import get_couchdb_connection
        try:
            db = get_couchdb_connection()
            if not db:
                print("CouchDB connection failed")
                return False
                
            user_doc = {
                'type': 'user',
                'postgres_id': self.id,
                'username': self.username,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'profile_picture': str(self.profile_picture) if self.profile_picture else None,
                'phone_number': self.phone_number,
                'address_text': self.address_text,
                'blockchain_address': self.blockchain_address,
                'is_identity_verified': self.is_identity_verified,
                'is_verified': self.is_verified,
                'document_ipfs_hash': self.document_ipfs_hash,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'last_login': self.last_login.isoformat() if self.last_login else None,
                'date_joined': self.date_joined.isoformat() if self.date_joined else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                user_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    user_doc['_rev'] = self.couchdb_rev

            # Save to CouchDB
            doc_id, doc_rev = db.save(user_doc)
            self.couchdb_id = doc_id
            self.couchdb_rev = doc_rev
            
            # Save again to store the CouchDB metadata, but avoid recursion
            User.objects.filter(id=self.id).update(couchdb_id=doc_id, couchdb_rev=doc_rev)
            
            print(f"Successfully synced user {self.username} to CouchDB")
            return True
            
        except Exception as e:
            print(f"Error syncing user {self.username} to CouchDB: {e}")
            return False

    def delete(self, *args, **kwargs):
        """Override delete to also remove from CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db and self.couchdb_id:
            try:
                doc = db[self.couchdb_id]
                db.delete(doc)
                print(f"Successfully deleted user {self.username} from CouchDB")
            except Exception as e:
                print(f"Error deleting user {self.username} from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update a user from CouchDB document"""
        try:
            user, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'username': couchdb_doc.get('username'),
                    'email': couchdb_doc.get('email'),
                    'first_name': couchdb_doc.get('first_name', ''),
                    'last_name': couchdb_doc.get('last_name', ''),
                    'phone_number': couchdb_doc.get('phone_number'),
                    'address_text': couchdb_doc.get('address_text'),
                    'blockchain_address': couchdb_doc.get('blockchain_address'),
                    'is_identity_verified': couchdb_doc.get('is_identity_verified', False),
                    'is_verified': couchdb_doc.get('is_verified', False),
                    'document_ipfs_hash': couchdb_doc.get('document_ipfs_hash'),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing user
                user.username = couchdb_doc.get('username', user.username)
                user.email = couchdb_doc.get('email', user.email)
                user.first_name = couchdb_doc.get('first_name', user.first_name)
                user.last_name = couchdb_doc.get('last_name', user.last_name)
                user.phone_number = couchdb_doc.get('phone_number', user.phone_number)
                user.address_text = couchdb_doc.get('address_text', user.address_text)
                user.blockchain_address = couchdb_doc.get('blockchain_address', user.blockchain_address)
                user.is_identity_verified = couchdb_doc.get('is_identity_verified', user.is_identity_verified)
                user.is_verified = couchdb_doc.get('is_verified', user.is_verified)
                user.document_ipfs_hash = couchdb_doc.get('document_ipfs_hash', user.document_ipfs_hash)
                user.couchdb_id = couchdb_doc.get('_id', user.couchdb_id)
                user.couchdb_rev = couchdb_doc.get('_rev', user.couchdb_rev)
                user.save()
            
            return user, created
        except Exception as e:
            print(f"Error creating user from CouchDB: {e}")
            return None, False
