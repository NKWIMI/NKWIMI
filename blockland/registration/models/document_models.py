# document_models.py
from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from .user_models import User
from .utils import validate_file_size

class PropertyDocument(models.Model):
    """Documents associated with properties with CouchDB integration"""
    DOCUMENT_TYPES = [
        ('DEED', 'Deed'),
        ('SURVEY', 'Survey'),
        ('CONTRACT', 'Contract'),
        ('OTHER', 'Other'),
    ]

    property = models.ForeignKey(
        'registration.Parcel',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='OTHER')
    file = models.FileField(upload_to='property_documents/%Y/%m/%d/', validators=[validate_file_size])
    description = models.TextField(blank=True)
    ipfs_hash = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Property Document"
        verbose_name_plural = "Property Documents"
        indexes = [
            models.Index(fields=['property']),
            models.Index(fields=['document_type']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.property.land_id}"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync document to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            document_doc = {
                'type': 'property_document',
                'postgres_id': self.id,
                'property_id': self.property.id,
                'property_couchdb_id': self.property.couchdb_id,
                'document_type': self.document_type,
                'file_path': str(self.file) if self.file else None,
                'description': self.description,
                'ipfs_hash': self.ipfs_hash,
                'uploaded_by_id': self.uploaded_by.id if self.uploaded_by else None,
                'uploaded_by_couchdb_id': self.uploaded_by.couchdb_id if self.uploaded_by else None,
                'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                document_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    document_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(document_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing document to CouchDB: {e}")
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
                print(f"Error deleting document from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update document from CouchDB document"""
        try:
            # Get property (Parcel) instance
            property_id = couchdb_doc.get('property_id')
            property_instance = None
            if property_id:
                try:
                    from .parcel_models import Parcel
                    property_instance = Parcel.objects.get(id=property_id)
                except Parcel.DoesNotExist:
                    print(f"Parcel with ID {property_id} not found")
                    return None, False

            # Get uploaded_by instance if exists
            uploaded_by_id = couchdb_doc.get('uploaded_by_id')
            uploaded_by = None
            if uploaded_by_id:
                try:
                    uploaded_by = User.objects.get(id=uploaded_by_id)
                except User.DoesNotExist:
                    print(f"Uploader with ID {uploaded_by_id} not found")

            uploaded_at = couchdb_doc.get('uploaded_at')
            if uploaded_at:
                uploaded_at = timezone.datetime.fromisoformat(uploaded_at)

            document, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'property': property_instance,
                    'document_type': couchdb_doc.get('document_type', 'OTHER'),
                    'file': couchdb_doc.get('file_path', ''),
                    'description': couchdb_doc.get('description', ''),
                    'ipfs_hash': couchdb_doc.get('ipfs_hash', ''),
                    'uploaded_by': uploaded_by,
                    'uploaded_at': uploaded_at,
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing document
                document.property = property_instance or document.property
                document.document_type = couchdb_doc.get('document_type', document.document_type)
                document.description = couchdb_doc.get('description', document.description)
                document.ipfs_hash = couchdb_doc.get('ipfs_hash', document.ipfs_hash)
                document.uploaded_by = uploaded_by or document.uploaded_by
                document.couchdb_id = couchdb_doc.get('_id', document.couchdb_id)
                document.couchdb_rev = couchdb_doc.get('_rev', document.couchdb_rev)
                document.save()
            
            return document, created
        except Exception as e:
            print(f"Error creating document from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('document_detail', kwargs={'pk': self.pk})

    # @property
    # def filename(self):
    #     """Return the filename without path"""
    #     return str(self.file).split('/')[-1] if self.file else ""