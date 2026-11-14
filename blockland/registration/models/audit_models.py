from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from .user_models import User

class AuditLog(models.Model):
    """System audit log for tracking important actions with CouchDB integration"""
    ACTION_CHOICES = [
        ('USER_CREATED', 'User Created'),
        ('USER_VERIFIED', 'User Verified'),
        ('PROPERTY_CREATED', 'Property Created'),
        ('PROPERTY_UPDATED', 'Property Updated'),
        ('TRANSFER_CREATED', 'Transfer Created'),
        ('TRANSFER_ACCEPTED', 'Transfer Accepted'),
        ('TRANSFER_REJECTED', 'Transfer Rejected'),
        ('TRANSFER_CANCELED', 'Transfer Canceled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    details = models.JSONField(default=dict)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} at {self.timestamp}"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync audit log to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            audit_doc = {
                'type': 'audit_log',
                'postgres_id': self.id,
                'user_id': self.user.id if self.user else None,
                'user_couchdb_id': self.user.couchdb_id if self.user else None,
                'action': self.action,
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'content_type_id': self.content_type.id if self.content_type else None,
                'object_id': self.object_id,
                'details': self.details
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                audit_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    audit_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(audit_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing audit log to CouchDB: {e}")
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
                print(f"Error deleting audit log from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update audit log from CouchDB document"""
        try:
            # Get user instance if exists
            user_id = couchdb_doc.get('user_id')
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    print(f"User with ID {user_id} not found")

            # Get content type instance if exists
            content_type_id = couchdb_doc.get('content_type_id')
            content_type = None
            if content_type_id:
                try:
                    content_type = ContentType.objects.get(id=content_type_id)
                except ContentType.DoesNotExist:
                    print(f"ContentType with ID {content_type_id} not found")

            timestamp = couchdb_doc.get('timestamp')
            if timestamp:
                timestamp = timezone.datetime.fromisoformat(timestamp)

            audit_log, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'user': user,
                    'action': couchdb_doc.get('action', ''),
                    'timestamp': timestamp,
                    'content_type': content_type,
                    'object_id': couchdb_doc.get('object_id'),
                    'details': couchdb_doc.get('details', {}),
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing audit log
                audit_log.user = user or audit_log.user
                audit_log.action = couchdb_doc.get('action', audit_log.action)
                audit_log.timestamp = timestamp or audit_log.timestamp
                audit_log.content_type = content_type or audit_log.content_type
                audit_log.object_id = couchdb_doc.get('object_id', audit_log.object_id)
                audit_log.details = couchdb_doc.get('details', audit_log.details)
                audit_log.couchdb_id = couchdb_doc.get('_id', audit_log.couchdb_id)
                audit_log.couchdb_rev = couchdb_doc.get('_rev', audit_log.couchdb_rev)
                audit_log.save()
            
            return audit_log, created
        except Exception as e:
            print(f"Error creating audit log from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('audit_log_detail', kwargs={'pk': self.pk})

    @property
    def formatted_timestamp(self):
        """Return formatted timestamp string"""
        return self.timestamp.strftime('%b %d, %Y %I:%M %p') if self.timestamp else ""


class MetadataVersion(models.Model):
    """Model for tracking metadata versions on blockchain with CouchDB integration"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    version = models.PositiveIntegerField()
    ipfs_hash = models.CharField(max_length=255)
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Changed from 'property' to 'property_data' to avoid conflict with Python's built-in property
    property_data = models.JSONField(blank=True, null=True)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        verbose_name = "Metadata Version"
        verbose_name_plural = "Metadata Versions"
        ordering = ['-created_at']
        unique_together = [['content_type', 'object_id', 'version']]
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['ipfs_hash']),
            models.Index(fields=['blockchain_tx_hash']),
            models.Index(fields=['created_at']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"Metadata v{self.version} for {self.content_object}"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync metadata version to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            metadata_doc = {
                'type': 'metadata_version',
                'postgres_id': self.id,
                'content_type_id': self.content_type.id if self.content_type else None,
                'object_id': self.object_id,
                'version': self.version,
                'ipfs_hash': self.ipfs_hash,
                'blockchain_tx_hash': self.blockchain_tx_hash,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'created_by_id': self.created_by.id if self.created_by else None,
                'created_by_couchdb_id': self.created_by.couchdb_id if self.created_by else None,
                'property': self.property_data  # FIXED: Changed from self.property to self.property_data
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
                print(f"Error syncing metadata version to CouchDB: {e}")
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
                print(f"Error deleting metadata version from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update metadata version from CouchDB document"""
        try:
            # Get content type instance
            content_type_id = couchdb_doc.get('content_type_id')
            content_type = None
            if content_type_id:
                try:
                    content_type = ContentType.objects.get(id=content_type_id)
                except ContentType.DoesNotExist:
                    print(f"ContentType with ID {content_type_id} not found")
                    return None, False

            # Get created_by instance if exists
            created_by_id = couchdb_doc.get('created_by_id')
            created_by = None
            if created_by_id:
                try:
                    created_by = User.objects.get(id=created_by_id)
                except User.DoesNotExist:
                    print(f"User with ID {created_by_id} not found")

            created_at = couchdb_doc.get('created_at')
            if created_at:
                created_at = timezone.datetime.fromisoformat(created_at)

            metadata_version, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'content_type': content_type,
                    'object_id': couchdb_doc.get('object_id', 0),
                    'version': couchdb_doc.get('version', 1),
                    'ipfs_hash': couchdb_doc.get('ipfs_hash', ''),
                    'blockchain_tx_hash': couchdb_doc.get('blockchain_tx_hash', ''),
                    'created_at': created_at,
                    'created_by': created_by,
                    'property_data': couchdb_doc.get('property', {}),  # FIXED: Changed from 'property' to 'property_data'
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing metadata version
                metadata_version.content_type = content_type or metadata_version.content_type
                metadata_version.object_id = couchdb_doc.get('object_id', metadata_version.object_id)
                metadata_version.version = couchdb_doc.get('version', metadata_version.version)
                metadata_version.ipfs_hash = couchdb_doc.get('ipfs_hash', metadata_version.ipfs_hash)
                metadata_version.blockchain_tx_hash = couchdb_doc.get('blockchain_tx_hash', metadata_version.blockchain_tx_hash)
                metadata_version.created_at = created_at or metadata_version.created_at
                metadata_version.created_by = created_by or metadata_version.created_by
                metadata_version.property_data = couchdb_doc.get('property', metadata_version.property_data)  # FIXED: Changed from property to property_data
                metadata_version.couchdb_id = couchdb_doc.get('_id', metadata_version.couchdb_id)
                metadata_version.couchdb_rev = couchdb_doc.get('_rev', metadata_version.couchdb_rev)
                metadata_version.save()
            
            return metadata_version, created
        except Exception as e:
            print(f"Error creating metadata version from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('metadata_version_detail', kwargs={'pk': self.pk})

    @property
    def short_ipfs_hash(self):
        """Return truncated IPFS hash for display"""
        return f"{self.ipfs_hash[:8]}...{self.ipfs_hash[-4:]}" if self.ipfs_hash else ""

    @property
    def short_tx_hash(self):
        """Return truncated transaction hash for display"""
        return f"{self.blockchain_tx_hash[:8]}...{self.blockchain_tx_hash[-4:]}" if self.blockchain_tx_hash else ""

    @property
    def formatted_created_at(self):
        """Return formatted created_at string"""
        return self.created_at.strftime('%b %d, %Y %I:%M %p') if self.created_at else ""