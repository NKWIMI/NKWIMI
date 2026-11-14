from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.apps import apps

class Command(BaseCommand):
    help = 'Completely reset the system by emptying all tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            confirm = input(
                "⚠️  WARNING: This will DELETE ALL DATA including users, parcels, and transfers. Continue? (yes/no): "
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        self.stdout.write(self.style.WARNING('Starting system reset...'))

        try:
            # Delete in correct order to respect foreign key constraints
            models_delete_order = [
                # Transfer-related models first
                ('registration', 'TransferHistory'),
                ('registration', 'PendingTransfer'),
                ('registration', 'Transfer'),
                ('registration', 'Transaction'),
                
                # Property and parcel models
                ('registration', 'PropertyParcelMetadata'),
                ('registration', 'PropertyParcel'),
                ('registration', 'PropertyDocument'),
                ('registration', 'Property'),
                ('registration', 'ParcelMetadata'),
                ('registration', 'Parcel'),
                
                # Blockchain models
                ('registration', 'BlockchainTransaction'),
                ('registration', 'Block'),
                ('registration', 'AuditLog'),
                ('registration', 'MetadataVersion'),
            ]

            deleted_counts = {}
            
            for app_label, model_name in models_delete_order:
                try:
                    model = apps.get_model(app_label, model_name)
                    count, _ = model.objects.all().delete()
                    deleted_counts[model_name] = count
                    self.stdout.write(self.style.SUCCESS(f'✓ Deleted {model_name}: {count} objects'))
                except LookupError:
                    self.stdout.write(self.style.WARNING(f'⚠ Model {model_name} not found'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠ Could not delete {model_name}: {e}'))

            # Delete non-admin users (keep superusers)
            User = get_user_model()
            non_admin_users = User.objects.filter(is_superuser=False)
            non_admin_count = non_admin_users.count()
            non_admin_users.delete()
            self.stdout.write(self.style.SUCCESS(f'✓ Deleted non-admin users: {non_admin_count}'))

            # Summary
            self.stdout.write(self.style.SUCCESS('\n✅ Django database reset completed!'))
            self.stdout.write(self.style.SUCCESS('Summary of deleted objects:'))
            for model_name, count in deleted_counts.items():
                self.stdout.write(self.style.SUCCESS(f'  - {model_name}: {count}'))
            self.stdout.write(self.style.SUCCESS(f'  - Non-admin users: {non_admin_count}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during reset: {e}'))