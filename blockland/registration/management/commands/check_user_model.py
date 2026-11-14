# registration/management/commands/check_user_model.py
from django.core.management.base import BaseCommand
from registration.models import User

class Command(BaseCommand):
    help = 'Check User model structure'

    def handle(self, *args, **options):
        self.stdout.write("🔍 User Model Structure")
        self.stdout.write("=" * 40)
        
        self.stdout.write(f"👤 User model: {User._meta.object_name}")
        self.stdout.write(f"   App: {User._meta.app_label}")
        self.stdout.write(f"   Table: {User._meta.db_table}")
        
        self.stdout.write(f"\n📋 User model fields:")
        for field in User._meta.fields:
            self.stdout.write(f"   {field.name} ({field.get_internal_type()})")
        
        self.stdout.write(f"\n🔗 User model related objects:")
        for rel in User._meta.related_objects:
            self.stdout.write(f"   {rel.name} -> {rel.related_model._meta.object_name}")