# registration/models/property_models.py

from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.core.validators import MinValueValidator
from web3 import Web3
from .user_models import User as User # Updated to match your custom user model
#from .utils import validate_file_size, FileExtensionValidator
from .utils import validate_file_size
from django.core.validators import FileExtensionValidator
from .document_models import PropertyDocument


class Property(models.Model):
    """Property model representing collections of land parcels with CouchDB integration"""
    PROPERTY_TYPES = [
        ('RESIDENTIAL', 'Residential'),
        ('COMMERCIAL', 'Commercial'),
        ('AGRICULTURAL', 'Agricultural'),
        ('INDUSTRIAL', 'Industrial'),
        ('OTHER', 'Other'),
    ]

    name = models.CharField(max_length=255, verbose_name="Property Name")
    property_id = models.CharField(max_length=50, unique=True, verbose_name="Property ID")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties', verbose_name="Owner")
    
    size_sqm = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0.01)], verbose_name="Total Size (square meters)"
    )
    location = models.CharField(max_length=255, verbose_name="Location")
    coordinates = models.JSONField(null=True, blank=True, verbose_name="Geo Coordinates")
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, default='RESIDENTIAL', verbose_name="Property Type")
    
    is_frozen = models.BooleanField(default=False, verbose_name="Frozen Status")
    blockchain_hash = models.CharField(max_length=66, blank=True, null=True, verbose_name="Blockchain Hash")
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property_id']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_frozen']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.property_id} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.blockchain_hash:
            self.blockchain_hash = Web3.keccak(text=self.property_id).hex()
        
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync property data to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            property_doc = {
                'type': 'property',
                'postgres_id': self.id,
                'name': self.name,
                'property_id': self.property_id,
                'owner_id': self.owner.id,
                'owner_couchdb_id': self.owner.couchdb_id,
                'owner_blockchain_address': self.owner.blockchain_address,
                'size_sqm': float(self.size_sqm) if self.size_sqm else None,
                'location': self.location,
                'coordinates': self.coordinates,
                'property_type': self.property_type,
                'is_frozen': self.is_frozen,
                'blockchain_hash': self.blockchain_hash,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                property_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    property_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(property_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing property to CouchDB: {e}")
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
                print(f"Error deleting property from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update a property from CouchDB document"""
        try:
            # Get owner instance
            owner_id = couchdb_doc.get('owner_id')
            owner = None
            if owner_id:
                try:
                    owner = User.objects.get(id=owner_id)
                except User.DoesNotExist:
                    print(f"Owner with ID {owner_id} not found")
                    return None, False

            property_obj, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'name': couchdb_doc.get('name'),
                    'property_id': couchdb_doc.get('property_id'),
                    'owner': owner,
                    'size_sqm': couchdb_doc.get('size_sqm'),
                    'location': couchdb_doc.get('location'),
                    'coordinates': couchdb_doc.get('coordinates'),
                    'property_type': couchdb_doc.get('property_type', 'RESIDENTIAL'),
                    'is_frozen': couchdb_doc.get('is_frozen', False),
                    'blockchain_hash': couchdb_doc.get('blockchain_hash'),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing property
                property_obj.name = couchdb_doc.get('name', property_obj.name)
                property_obj.property_id = couchdb_doc.get('property_id', property_obj.property_id)
                property_obj.owner = owner or property_obj.owner
                property_obj.size_sqm = couchdb_doc.get('size_sqm', property_obj.size_sqm)
                property_obj.location = couchdb_doc.get('location', property_obj.location)
                property_obj.coordinates = couchdb_doc.get('coordinates', property_obj.coordinates)
                property_obj.property_type = couchdb_doc.get('property_type', property_obj.property_type)
                property_obj.is_frozen = couchdb_doc.get('is_frozen', property_obj.is_frozen)
                property_obj.blockchain_hash = couchdb_doc.get('blockchain_hash', property_obj.blockchain_hash)
                property_obj.couchdb_id = couchdb_doc.get('_id', property_obj.couchdb_id)
                property_obj.couchdb_rev = couchdb_doc.get('_rev', property_obj.couchdb_rev)
                property_obj.save()
            
            return property_obj, created
        except Exception as e:
            print(f"Error creating property from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('property_detail', kwargs={'pk': self.pk})

    @property
    def parcel_count(self):
        return self.parcels.count()


class PropertyParcel(models.Model):
    """Land parcel model (used within Property) with blockchain and CouchDB integration"""
    PARCEL_TYPES = [
        ('RESIDENTIAL', 'Residential'),
        ('COMMERCIAL', 'Commercial'),
        ('AGRICULTURAL', 'Agricultural'),
        ('INDUSTRIAL', 'Industrial'),
        ('VACANT', 'Vacant Land'),
    ]

    related_property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='parcels', verbose_name="Property")
    parcel_id = models.CharField(max_length=50, unique=True, verbose_name="Parcel ID")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_parcels', verbose_name="Owner")
    
    size_sqm = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(0.01)], verbose_name="Size (square meters)")
    address = models.CharField(max_length=255, verbose_name="Physical Address")
    coordinates = models.JSONField(verbose_name="Geo Coordinates", help_text="GeoJSON formatted coordinates")
    parcel_type = models.CharField(max_length=20, choices=PARCEL_TYPES, default='VACANT', verbose_name="Parcel Type")
    
    is_registered = models.BooleanField(default=False, verbose_name="Registration Status")
    registration_date = models.DateTimeField(null=True, blank=True, verbose_name="Registration Date")
    
    blockchain_hash = models.CharField(max_length=66, blank=True, null=True, verbose_name="Blockchain Hash")
    transaction_hash = models.CharField(max_length=66, blank=True, null=True, verbose_name="Transaction Hash")
    is_frozen = models.BooleanField(default=False, verbose_name="Frozen Status")
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    class Meta:
        verbose_name = "Property Parcel"
        verbose_name_plural = "Property Parcels"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parcel_id']),
            models.Index(fields=['owner']),
            models.Index(fields=['is_registered']),
            models.Index(fields=['is_frozen']),
            models.Index(fields=['couchdb_id']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(size_sqm__gte=0.01), name="min_property_parcel_size")
        ]

    def __str__(self):
        return f"Property Parcel {self.parcel_id} - {self.address}"

    def save(self, *args, **kwargs):
        if not self.blockchain_hash:
            self.blockchain_hash = Web3.keccak(text=self.parcel_id).hex()
        
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync parcel data to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            parcel_doc = {
                'type': 'property_parcel',
                'postgres_id': self.id,
                'parcel_id': self.parcel_id,
                'related_property_id': self.related_property.id,
                'related_property_couchdb_id': self.related_property.couchdb_id,
                'owner_id': self.owner.id,
                'owner_couchdb_id': self.owner.couchdb_id,
                'owner_blockchain_address': self.owner.blockchain_address,
                'size_sqm': float(self.size_sqm) if self.size_sqm else None,
                'address': self.address,
                'coordinates': self.coordinates,
                'parcel_type': self.parcel_type,
                'is_registered': self.is_registered,
                'registration_date': self.registration_date.isoformat() if self.registration_date else None,
                'blockchain_hash': self.blockchain_hash,
                'transaction_hash': self.transaction_hash,
                'is_frozen': self.is_frozen,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                parcel_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    parcel_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(parcel_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing parcel to CouchDB: {e}")
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
                print(f"Error deleting parcel from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update a parcel from CouchDB document"""
        try:
            # Get related property instance
            property_id = couchdb_doc.get('related_property_id')
            related_property = None
            if property_id:
                try:
                    related_property = Property.objects.get(id=property_id)
                except Property.DoesNotExist:
                    print(f"Property with ID {property_id} not found")
                    return None, False

            # Get owner instance
            owner_id = couchdb_doc.get('owner_id')
            owner = None
            if owner_id:
                try:
                    owner = User.objects.get(id=owner_id)
                except User.DoesNotExist:
                    print(f"Owner with ID {owner_id} not found")
                    return None, False

            registration_date = couchdb_doc.get('registration_date')
            if registration_date:
                registration_date = timezone.datetime.fromisoformat(registration_date)

            parcel, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'parcel_id': couchdb_doc.get('parcel_id'),
                    'related_property': related_property,
                    'owner': owner,
                    'size_sqm': couchdb_doc.get('size_sqm'),
                    'address': couchdb_doc.get('address'),
                    'coordinates': couchdb_doc.get('coordinates'),
                    'parcel_type': couchdb_doc.get('parcel_type', 'VACANT'),
                    'is_registered': couchdb_doc.get('is_registered', False),
                    'registration_date': registration_date,
                    'blockchain_hash': couchdb_doc.get('blockchain_hash'),
                    'transaction_hash': couchdb_doc.get('transaction_hash'),
                    'is_frozen': couchdb_doc.get('is_frozen', False),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing parcel
                parcel.parcel_id = couchdb_doc.get('parcel_id', parcel.parcel_id)
                parcel.related_property = related_property or parcel.related_property
                parcel.owner = owner or parcel.owner
                parcel.size_sqm = couchdb_doc.get('size_sqm', parcel.size_sqm)
                parcel.address = couchdb_doc.get('address', parcel.address)
                parcel.coordinates = couchdb_doc.get('coordinates', parcel.coordinates)
                parcel.parcel_type = couchdb_doc.get('parcel_type', parcel.parcel_type)
                parcel.is_registered = couchdb_doc.get('is_registered', parcel.is_registered)
                parcel.registration_date = registration_date or parcel.registration_date
                parcel.blockchain_hash = couchdb_doc.get('blockchain_hash', parcel.blockchain_hash)
                parcel.transaction_hash = couchdb_doc.get('transaction_hash', parcel.transaction_hash)
                parcel.is_frozen = couchdb_doc.get('is_frozen', parcel.is_frozen)
                parcel.couchdb_id = couchdb_doc.get('_id', parcel.couchdb_id)
                parcel.couchdb_rev = couchdb_doc.get('_rev', parcel.couchdb_rev)
                parcel.save()
            
            return parcel, created
        except Exception as e:
            print(f"Error creating parcel from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('property_parcel_detail', kwargs={'pk': self.pk})

    @property
    def current_status(self):
        return "Frozen" if self.is_frozen else ("Registered" if self.is_registered else "Unregistered")


class PropertyParcelMetadata(models.Model):
    """Model tracking historical changes and documents for PropertyParcel with CouchDB integration"""
    parcel = models.ForeignKey(PropertyParcel, on_delete=models.CASCADE, related_name='metadata_versions', verbose_name="Related Parcel")
    ipfs_hash = models.CharField(max_length=100, blank=True, null=True, verbose_name="IPFS Hash")
    document = models.ForeignKey(PropertyDocument, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Document")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Uploaded By")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Version Date")
    notes = models.TextField(blank=True, verbose_name="Version Notes")
    is_status_change = models.BooleanField(default=False, verbose_name="Status Change")
    transaction_hash = models.CharField(max_length=66, blank=True, null=True, verbose_name="Blockchain TX Hash")
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        verbose_name = "Property Parcel Metadata"
        verbose_name_plural = "Property Parcel Metadata Versions"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['parcel', 'timestamp']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"Metadata for {self.parcel.parcel_id} ({self.timestamp})"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync metadata to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            metadata_doc = {
                'type': 'property_parcel_metadata',
                'postgres_id': self.id,
                'parcel_id': self.parcel.id,
                'parcel_couchdb_id': self.parcel.couchdb_id,
                'ipfs_hash': self.ipfs_hash,
                'document_id': self.document.id if self.document else None,
                'uploader_id': self.uploader.id if self.uploader else None,
                'uploader_couchdb_id': self.uploader.couchdb_id if self.uploader else None,
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'notes': self.notes,
                'is_status_change': self.is_status_change,
                'transaction_hash': self.transaction_hash,
                'created_at': self.timestamp.isoformat() if self.timestamp else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                metadata_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    metadata_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(metadata_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing metadata to CouchDB: {e}")
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
                print(f"Error deleting metadata from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('property_parcel_metadata_detail', kwargs={'pk': self.pk})
