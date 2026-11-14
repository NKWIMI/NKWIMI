# registration/models/parcel_models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
import re

User = get_user_model()


class Parcel(models.Model):
    """Model representing a land parcel"""
    LAND_ID_MAX_LENGTH = 64
    ADDRESS_MAX_LENGTH = 42
    IPFS_HASH_MAX_LENGTH = 100
    TX_HASH_MAX_LENGTH = 66

    land_id = models.CharField(max_length=LAND_ID_MAX_LENGTH, unique=True)
    owner_address = models.CharField(max_length=ADDRESS_MAX_LENGTH)
    size_sqm = models.DecimalField(max_digits=10, decimal_places=2)
    coordinates = models.JSONField(null=True, blank=True)
    latest_ipfs_hash = models.CharField(max_length=IPFS_HASH_MAX_LENGTH, blank=True)
    transaction_hash = models.CharField(max_length=TX_HASH_MAX_LENGTH, blank=True)
    is_frozen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add the contract_file field
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)

    owner = models.ForeignKey(
        'registration.User',
        on_delete=models.PROTECT,
        related_name='parcels'
    )

    class Meta:
        verbose_name = "Parcel"
        verbose_name_plural = "Parcels"
        ordering = ['-created_at']

    def __str__(self):
        return f"Parcel {self.land_id}"

    def get_absolute_url(self):
        return reverse('parcel_detail', kwargs={'pk': self.pk})

    def clean(self):
        """Validate that owner_address matches owner's blockchain_address"""
        super().clean()
        
        # If owner is set and has a blockchain_address, ensure consistency
        if self.owner and self.owner.blockchain_address:
            if self.owner_address.lower() != self.owner.blockchain_address.lower():
                raise ValidationError({
                    'owner_address': f"Owner address must match the owner's blockchain address. "
                                   f"Expected: {self.owner.blockchain_address}, Got: {self.owner_address}"
                })
        
        # Validate Ethereum address format
        if self.owner_address and not self._is_valid_ethereum_address(self.owner_address):
            raise ValidationError({
                'owner_address': "Invalid Ethereum address format"
            })

    def save(self, *args, **kwargs):
        """Ensure owner_address is synchronized with owner's blockchain_address"""
        # Auto-populate owner_address from owner if not set
        if self.owner and self.owner.blockchain_address and not self.owner_address:
            self.owner_address = self.owner.blockchain_address
        
        # Always sync owner_address with owner's blockchain_address
        if self.owner and self.owner.blockchain_address:
            self.owner_address = self.owner.blockchain_address
        
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def _is_valid_ethereum_address(self, address):
        """Check if the address is a valid Ethereum address"""
        if not address:
            return False
        
        # Basic Ethereum address validation (0x followed by 40 hex characters)
        pattern = r'^0x[a-fA-F0-9]{40}$'
        return bool(re.match(pattern, address))

    @property
    def is_owned_by_user(self, user):
        """Check if the parcel is owned by the given user"""
        if not user or not user.blockchain_address:
            return False
        return self.owner_address.lower() == user.blockchain_address.lower()

    @property
    def short_transaction_hash(self):
        """Return shortened transaction hash for display"""
        if self.transaction_hash:
            return f"{self.transaction_hash[:8]}...{self.transaction_hash[-6:]}"
        return ""

    @property
    def display_coordinates(self):
        """Return coordinates in a display-friendly format"""
        if self.coordinates and 'lat' in self.coordinates and 'lng' in self.coordinates:
            return f"{self.coordinates['lat']}, {self.coordinates['lng']}"
        return "Not set"


class ParcelMetadata(models.Model):
    """Model tracking historical metadata versions for parcels"""
    parcel = models.ForeignKey(
        Parcel,
        on_delete=models.CASCADE,
        related_name='metadata_versions'
    )
    ipfs_hash = models.CharField(max_length=Parcel.IPFS_HASH_MAX_LENGTH)
    document = models.ForeignKey(
        'registration.PropertyDocument',
        on_delete=models.CASCADE,
        related_name='parcel_metadata',
        null=True,
        blank=True
    )
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    is_status_change = models.BooleanField(default=False)
    transaction_hash = models.CharField(max_length=Parcel.TX_HASH_MAX_LENGTH, blank=True)

    class Meta:
        verbose_name = "Parcel Metadata Version"
        verbose_name_plural = "Parcel Metadata Versions"
        ordering = ['-created_at']

    def __str__(self):
        return f"Metadata v.{self.id} for {self.parcel.land_id}"

    def get_absolute_url(self):
        return reverse('parcel_metadata', kwargs={'pk': self.parcel.pk})

    @property
    def short_hash(self):
        return f"{self.ipfs_hash[:8]}...{self.ipfs_hash[-4:]}" if self.ipfs_hash else ""

    @property
    def short_transaction_hash(self):
        """Return shortened transaction hash for display"""
        if self.transaction_hash:
            return f"{self.transaction_hash[:8]}...{self.transaction_hash[-6:]}"
        return ""