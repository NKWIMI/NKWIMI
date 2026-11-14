# registration/management/commands/sync_users_to_couchdb.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync User models from SQLite to CouchDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all users (including already synced ones)',
        )
        parser.add_argument(
            '--user-ids',
            type=str,
            help='Comma-separated list of user IDs to sync',
        )

    def handle(self, *args, **options):
        if not hasattr(settings, 'COUCHDB_CONNECTION') or not settings.COUCHDB_CONNECTION:
            self.stdout.write(self.style.ERROR('CouchDB not configured or connected'))
            return

        User = get_user_model()
        
        # Get users to sync
        if options['user_ids']:
            user_ids = [int(id.strip()) for id in options['user_ids'].split(',')]
            users = User.objects.filter(id__in=user_ids)
        elif options['all']:
            users = User.objects.all()
        else:
            # Default: sync only users that haven't been synced or need update
            users = User.objects.all()
        
        success_count = 0
        total_count = users.count()
        
        self.stdout.write(f'🔄 Syncing {total_count} users to CouchDB...')
        
        for user in users:
            if self.sync_user(user):
                success_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Successfully synced {success_count}/{total_count} users to CouchDB')
        )

    def sync_user(self, user):
        """Sync a single user to CouchDB"""
        try:
            user_data = {
                '_id': f'user_{user.id}',
                'type': 'user',
                'django_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_verified': getattr(user, 'is_verified', False),
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'blockchain_address': getattr(user, 'blockchain_address', ''),
                'sync_timestamp': timezone.now().isoformat(),
                'model_type': 'user'
            }
            
            # Check if document already exists
            doc_id = f'user_{user.id}'
            couchdb = settings.COUCHDB_CONNECTION
            
            if doc_id in couchdb:
                doc = couchdb[doc_id]
                user_data['_rev'] = doc['_rev']
            
            couchdb.save(user_data)
            self.stdout.write(f'Synced user {user.username} (ID: {user.id})')
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error syncing user {user.username}: {str(e)}')
            )
            logger.error("Error syncing user %s: %s", user.username, str(e))
            return False