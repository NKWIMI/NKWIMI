from django.core.management.base import BaseCommand
from registration import couchdb_utils
import couchdb
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset CouchDB land_registration database by deleting all documents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            confirm = input(
                "⚠️  WARNING: This will DELETE ALL DATA from CouchDB land_registration. Continue? (yes/no): "
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        self.stdout.write(self.style.WARNING('Starting CouchDB land_registration reset...'))

        try:
            # Method 1: Try to get land_registration through direct connection
            self.stdout.write('Attempting direct connection to land_registration...')
            
            # Create a new connection to land_registration
            land_db = self.connect_to_land_registration()
            
            if land_db:
                self.reset_database(land_db)
            else:
                self.stdout.write(self.style.ERROR('❌ Could not connect to land_registration database'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error resetting CouchDB: {e}'))

    def connect_to_land_registration(self):
        """Create direct connection to land_registration database"""
        try:
            # Get connection settings from your current connection
            current_db = couchdb_utils.get_couchdb_connection()
            
            # Extract server URL from current connection
            resource_url = current_db.resource.url
            # The URL format is usually: http://localhost:5984/database_name
            server_url = '/'.join(resource_url.split('/')[:-1])  # Remove database part
            
            self.stdout.write(f'Server URL: {server_url}')
            
            # Get credentials from settings or use defaults
            username = getattr(settings, 'COUCHDB_USERNAME', 'admin')
            password = getattr(settings, 'COUCHDB_PASSWORD', 'password')
            
            # Connect to server
            server = couchdb.Server(server_url)
            if username and password:
                server.resource.credentials = (username, password)
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to CouchDB server'))
            self.stdout.write(f'Available databases: {list(server)}')
            
            # Connect to land_registration
            if 'land_registration' in server:
                land_db = server['land_registration']
                self.stdout.write(self.style.SUCCESS('✓ Connected to database: land_registration'))
                return land_db
            else:
                self.stdout.write(self.style.ERROR('❌ land_registration database not found on server'))
                return None
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error connecting to land_registration: {e}'))
            return None

    def reset_database(self, land_db):
        """Reset the land_registration database"""
        try:
            # Get all documents
            all_docs = land_db.view('_all_docs', include_docs=True)
            user_docs = [row for row in all_docs if not row['id'].startswith('_')]
            
            self.stdout.write(self.style.WARNING(f'📄 Found {len(user_docs)} documents to delete'))
            
            if not user_docs:
                self.stdout.write(self.style.SUCCESS('✅ Database is already empty!'))
                return
            
            # Delete all user documents
            deleted_count = 0
            for row in all_docs:
                doc_id = row['id']
                # Skip design documents and system documents
                if not doc_id.startswith('_'):
                    try:
                        doc = row['doc']
                        land_db.delete(doc)
                        deleted_count += 1
                        if deleted_count <= 10:  # Show first 10 deletions
                            self.stdout.write(self.style.SUCCESS(f'✓ Deleted: {doc_id}'))
                        elif deleted_count == 11:
                            self.stdout.write('... (more documents being deleted)')
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'⚠ Could not delete {doc_id}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'✅ CouchDB land_registration reset completed! Deleted {deleted_count} documents.'))
            
            # Verify
            all_docs_after = land_db.view('_all_docs', include_docs=True)
            user_docs_after = [row for row in all_docs_after if not row['id'].startswith('_')]
            self.stdout.write(f'Documents remaining: {len(user_docs_after)}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during database reset: {e}'))