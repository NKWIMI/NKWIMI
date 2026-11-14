# registration/management/commands/debug_users.py
from django.core.management.base import BaseCommand
from registration.models import User
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Debug user wallet setup'

    def handle(self, *args, **options):
        self.stdout.write("🔍 User Wallet Debug Information")
        self.stdout.write("=" * 50)
        
        users = User.objects.all()
        
        if not users:
            self.stdout.write(self.style.WARNING("❌ No users found in database"))
            return
            
        for user in users:
            self.stdout.write(f"\n👤 User: {user.username} (ID: {user.id})")
            self.stdout.write(f"   Email: {user.email}")
            self.stdout.write(f"   Is Active: {user.is_active}")
            self.stdout.write(f"   Blockchain Address: {user.blockchain_address}")
            self.stdout.write(f"   Has Private Key: {bool(user.encrypted_private_key)}")
            
            # Test blockchain service with this user
            try:
                blockchain = BlockchainService(user=user)
                if blockchain.account:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Blockchain Account: {blockchain.account.address}"))
                else:
                    self.stdout.write(self.style.ERROR("   ❌ No blockchain account available"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ BlockchainService error: {e}"))
                
        self.stdout.write("\n✅ Debug completed")