from django.core.management.base import BaseCommand
from registration import couchdb_utils

class Command(BaseCommand):
    help = 'Fix CouchDB document conflicts'

    def handle(self, *args, **options):
        self.stdout.write("🔧 Fixing CouchDB conflicts...")
        
        db = couchdb_utils.get_couchdb_connection()
        
        # Get all documents with conflicts
        all_docs = db.view('_all_docs', include_docs=True, conflicts=True)
        
        fixed_count = 0
        for row in all_docs:
            if hasattr(row, 'doc') and hasattr(row.doc, '_conflicts'):
                doc = row.doc
                conflicts = getattr(doc, '_conflicts', [])
                
                if conflicts:
                    self.stdout.write(f"⚠️ Document {doc['_id']} has {len(conflicts)} conflicts")
                    
                    # Delete conflicting revisions
                    for conflict_rev in conflicts:
                        try:
                            conflict_doc = db.get(doc['_id'], rev=conflict_rev)
                            db.delete(conflict_doc)
                            self.stdout.write(f"✓ Deleted conflict revision: {conflict_rev}")
                        except Exception as e:
                            self.stdout.write(f"❌ Could not delete conflict: {e}")
                    
                    fixed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"✅ Fixed conflicts in {fixed_count} documents"))