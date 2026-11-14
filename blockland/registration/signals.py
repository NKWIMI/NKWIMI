# registration/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings
from datetime import datetime
import couchdb

# Global flags for optional features
AI_AVAILABLE = False
IDENTITY_DOCUMENT_AVAILABLE = False

# Try to import optional modules (do this at the top level to avoid circular imports)
try:
    from registration.models import IdentityDocument
    IDENTITY_DOCUMENT_AVAILABLE = True
except ImportError:
    IDENTITY_DOCUMENT_AVAILABLE = False

try:
    from ai.services.document_ai_service import DocumentAIService
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️ AI module not available. Document verification will use basic validation.")

def get_couchdb_db():
    """Safe way to get CouchDB database instance"""
    try:
        return settings.COUCHDB_DB
    except AttributeError:
        return None

# AI Document Verification Signal
if AI_AVAILABLE and IDENTITY_DOCUMENT_AVAILABLE:
    @receiver(pre_save, sender=IdentityDocument)
    def verify_identity_document(sender, instance, **kwargs):
        """AI document verification before saving"""
        # Import here to avoid circular imports
        from registration.models import IdentityDocument
        
        if instance.document_file and not instance.is_verified:
            try:
                ai_service = DocumentAIService()
                
                risk_score, warnings = ai_service.generate_risk_score(
                    instance.document_file, instance.user
                )
                
                instance.risk_score = risk_score
                instance.verification_warnings = "\n".join(warnings) if warnings else ""
                instance.is_verified = risk_score < 50  # Auto-verify if low risk
                
                if risk_score >= 50:
                    instance.verification_status = 'requires_review'
                else:
                    instance.verification_status = 'verified'
                    
            except Exception as e:
                # Fallback if AI service fails
                instance.verification_status = 'pending'
                instance.risk_score = 0
                instance.verification_warnings = f"AI verification failed: {str(e)}"

# CouchDB Synchronization Signals
@receiver(post_save)
def sync_to_couchdb(sender, instance, created, **kwargs):
    """Generic sync to CouchDB for supported models"""
    # Import models here to avoid circular imports
    from registration.models import Block, BlockchainTransaction
    
    couchdb_db = get_couchdb_db()
    if not couchdb_db:
        return
    
    model_name = sender.__name__
    
    try:
        if sender == Block:
            # Convert model instance to dictionary
            block_data = {
                '_id': f'block_{instance.id}',
                'type': 'block',
                'hash': instance.hash,
                'height': instance.height,
                'timestamp': instance.timestamp.isoformat() if instance.timestamp else None,
                'previous_hash': instance.previous_hash,
                'nonce': instance.nonce,
                'difficulty': str(instance.difficulty) if instance.difficulty else None,
                'gas_used': instance.gas_used,
                'gas_limit': instance.gas_limit,
                'miner': instance.miner,
                'django_id': instance.id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            doc_id = f'block_{instance.id}'
            
        elif sender == BlockchainTransaction:
            transaction_data = {
                '_id': f'tx_{instance.id}',
                'type': 'transaction',
                'tx_hash': instance.tx_hash,
                'block_id': instance.block.id if instance.block else None,
                'block_hash': instance.block.hash if instance.block else None,
                'block_height': instance.block.height if instance.block else None,
                'sender': instance.sender,
                'recipient': instance.recipient,
                'amount': float(instance.amount) if instance.amount else None,
                'fee': float(instance.fee) if instance.fee else None,
                'timestamp': instance.timestamp.isoformat() if instance.timestamp else None,
                'status': instance.status,
                'django_id': instance.id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            doc_id = f'tx_{instance.id}'
            data_to_save = transaction_data
            
        else:
            # Not a supported model for CouchDB sync
            return
        
        # Check if document already exists (for updates)
        try:
            existing_doc = couchdb_db[doc_id]
            data_to_save['_rev'] = existing_doc['_rev']  # Include revision for updates
        except couchdb.ResourceNotFound:
            pass  # New document, no revision needed
        
        # Save to CouchDB and get the revision
        saved_doc_id, doc_rev = couchdb_db.save(data_to_save)
        
        # Update the model with CouchDB metadata (without triggering save signal again)
        if sender == Block:
            Block.objects.filter(id=instance.id).update(
                couchdb_id=saved_doc_id,
                couchdb_rev=doc_rev
            )
        elif sender == BlockchainTransaction:
            BlockchainTransaction.objects.filter(id=instance.id).update(
                couchdb_id=saved_doc_id,
                couchdb_rev=doc_rev
            )
        
        print(f"✅ {model_name} {instance.id} synced to CouchDB with ID: {saved_doc_id}")
        
    except Exception as e:
        print(f"❌ Error syncing {model_name} {instance.id} to CouchDB: {e}")

@receiver(post_delete)
def delete_from_couchdb(sender, instance, **kwargs):
    """Generic delete from CouchDB for supported models"""
    # Import models here to avoid circular imports
    from registration.models import Block, BlockchainTransaction
    
    couchdb_db = get_couchdb_db()
    if not couchdb_db:
        return
    
    model_name = sender.__name__
    
    try:
        if sender == Block:
            doc_id = f'block_{instance.id}'
        elif sender == BlockchainTransaction:
            doc_id = f'tx_{instance.id}'
        else:
            # Not a supported model for CouchDB sync
            return
        
        doc = couchdb_db[doc_id]
        couchdb_db.delete(doc)
        print(f"✅ {model_name} {instance.id} deleted from CouchDB")
        
    except couchdb.ResourceNotFound:
        print(f"⚠️ {model_name} {instance.id} not found in CouchDB during deletion")
    except Exception as e:
        print(f"❌ Error deleting {model_name} {instance.id} from CouchDB: {e}")

# Additional signal for IdentityDocument if available
if IDENTITY_DOCUMENT_AVAILABLE:
    @receiver(post_save, sender=IdentityDocument)
    def sync_identity_document_to_couchdb(sender, instance, created, **kwargs):
        """Sync IdentityDocument to CouchDB for audit purposes"""
        couchdb_db = get_couchdb_db()
        if not couchdb_db or not instance.user:
            return
        
        try:
            doc_data = {
                '_id': f'identity_doc_{instance.id}',
                'type': 'identity_document',
                'user_id': instance.user.id,
                'user_email': instance.user.email,
                'document_type': instance.document_type,
                'risk_score': instance.risk_score,
                'is_verified': instance.is_verified,
                'verification_status': instance.verification_status,
                'verification_warnings': instance.verification_warnings,
                'django_id': instance.id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if document already exists
            try:
                existing_doc = couchdb_db[f'identity_doc_{instance.id}']
                doc_data['_rev'] = existing_doc['_rev']
            except couchdb.ResourceNotFound:
                pass
            
            # Save to CouchDB
            doc_id, doc_rev = couchdb_db.save(doc_data)
            
            # Update model with CouchDB metadata
            IdentityDocument.objects.filter(id=instance.id).update(
                couchdb_id=doc_id,
                couchdb_rev=doc_rev
            )
            
            print(f"✅ Identity Document {instance.id} synced to CouchDB")
            
        except Exception as e:
            print(f"❌ Error syncing identity document {instance.id} to CouchDB: {e}")

    @receiver(post_delete, sender=IdentityDocument)
    def delete_identity_document_from_couchdb(sender, instance, **kwargs):
        """Delete IdentityDocument from CouchDB when Django object is deleted"""
        couchdb_db = get_couchdb_db()
        if not couchdb_db:
            return
        
        try:
            doc_id = f'identity_doc_{instance.id}'
            doc = couchdb_db[doc_id]
            couchdb_db.delete(doc)
            print(f"✅ Identity Document {instance.id} deleted from CouchDB")
        except couchdb.ResourceNotFound:
            print(f"⚠️ Identity Document {instance.id} not found in CouchDB during deletion")
        except Exception as e:
            print(f"❌ Error deleting identity document {instance.id} from CouchDB: {e}")

# Make sure to connect the generic signals
def ready(self):
    """Connect the generic signals"""
    from django.apps import apps
    from registration.models import Block, BlockchainTransaction
    
    # Disconnect specific signals if they were connected elsewhere
    post_save.disconnect(sync_to_couchdb, sender=Block)
    post_save.disconnect(sync_to_couchdb, sender=BlockchainTransaction)
    post_delete.disconnect(delete_from_couchdb, sender=Block)
    post_delete.disconnect(delete_from_couchdb, sender=BlockchainTransaction)
    
    # Reconnect generic signals
    post_save.connect(sync_to_couchdb, sender=Block)
    post_save.connect(sync_to_couchdb, sender=BlockchainTransaction)
    post_delete.connect(delete_from_couchdb, sender=Block)
    post_delete.connect(delete_from_couchdb, sender=BlockchainTransaction)