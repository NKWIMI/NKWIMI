from django.db import models
from django.utils import timezone
from django.urls import reverse

class ContactSubmission(models.Model):
    """Model for contact form submissions with CouchDB integration"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    ip_address = models.CharField(max_length=50, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    
    # CouchDB Integration
    couchdb_id = models.CharField(max_length=255, blank=True, null=True, editable=False)
    couchdb_rev = models.CharField(max_length=255, blank=True, null=True, editable=False)

    class Meta:
        ordering = ['-submission_date']
        verbose_name = 'Contact Form Submission'
        verbose_name_plural = 'Contact Form Submissions'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['submission_date']),
            models.Index(fields=['couchdb_id']),
        ]

    def __str__(self):
        return f"{self.name} - {self.submission_date.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        # Sync to CouchDB after saving to PostgreSQL
        super().save(*args, **kwargs)
        self.sync_to_couchdb()

    def sync_to_couchdb(self):
        """Sync contact submission to CouchDB"""
        from .utils import get_couchdb_connection
        db = get_couchdb_connection()
        if db:
            contact_doc = {
                'type': 'contact_submission',
                'postgres_id': self.id,
                'name': self.name,
                'email': self.email,
                'message': self.message,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'submission_date': self.submission_date.isoformat() if self.submission_date else None
            }

            # If we already have a CouchDB ID, include it for update
            if self.couchdb_id:
                contact_doc['_id'] = self.couchdb_id
                if self.couchdb_rev:
                    contact_doc['_rev'] = self.couchdb_rev

            try:
                doc_id, doc_rev = db.save(contact_doc)
                self.couchdb_id = doc_id
                self.couchdb_rev = doc_rev
                # Save again to store the CouchDB metadata, but avoid infinite recursion
                super().save(update_fields=['couchdb_id', 'couchdb_rev'])
                return True
            except Exception as e:
                print(f"Error syncing contact submission to CouchDB: {e}")
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
                print(f"Error deleting contact submission from CouchDB: {e}")
        
        super().delete(*args, **kwargs)

    @classmethod
    def from_couchdb(cls, couchdb_doc):
        """Create or update contact submission from CouchDB document"""
        try:
            submission_date = couchdb_doc.get('submission_date')
            if submission_date:
                submission_date = timezone.datetime.fromisoformat(submission_date)

            submission, created = cls.objects.get_or_create(
                id=couchdb_doc.get('postgres_id'),
                defaults={
                    'name': couchdb_doc.get('name', ''),
                    'email': couchdb_doc.get('email', ''),
                    'message': couchdb_doc.get('message', ''),
                    'ip_address': couchdb_doc.get('ip_address', ''),
                    'user_agent': couchdb_doc.get('user_agent', ''),
                    'submission_date': submission_date,
                    'couchdb_id': couchdb_doc.get('_id'),
                    'couchdb_rev': couchdb_doc.get('_rev'),
                }
            )
            
            if not created:
                # Update existing submission
                submission.name = couchdb_doc.get('name', submission.name)
                submission.email = couchdb_doc.get('email', submission.email)
                submission.message = couchdb_doc.get('message', submission.message)
                submission.ip_address = couchdb_doc.get('ip_address', submission.ip_address)
                submission.user_agent = couchdb_doc.get('user_agent', submission.user_agent)
                submission.couchdb_id = couchdb_doc.get('_id', submission.couchdb_id)
                submission.couchdb_rev = couchdb_doc.get('_rev', submission.couchdb_rev)
                submission.save()
            
            return submission, created
        except Exception as e:
            print(f"Error creating contact submission from CouchDB: {e}")
            return None, False

    def get_absolute_url(self):
        return reverse('contact_submission_detail', kwargs={'pk': self.pk})

    @property
    def short_message(self):
        """Return truncated message for display"""
        if len(self.message) > 100:
            return f"{self.message[:100]}..."
        return self.message

    @property
    def formatted_date(self):
        """Return formatted date string"""
        return self.submission_date.strftime('%b %d, %Y %I:%M %p') if self.submission_date else ""
