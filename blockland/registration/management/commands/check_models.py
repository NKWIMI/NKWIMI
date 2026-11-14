# registration/management/commands/check_models.py
from django.core.management.base import BaseCommand
import registration.models as models

class Command(BaseCommand):
    help = 'Check what models exist in registration app'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking registration models...")
        
        # List all attributes in registration.models that are likely Django models
        for attr_name in dir(models):
            attr = getattr(models, attr_name)
            if hasattr(attr, '_meta') and hasattr(attr._meta, 'app_label'):
                self.stdout.write(f"✅ Model found: {attr_name}")
                self.stdout.write(f"   App: {attr._meta.app_label}")
                self.stdout.write(f"   DB Table: {attr._meta.db_table}")
        
        self.stdout.write("\n✅ Model check completed")