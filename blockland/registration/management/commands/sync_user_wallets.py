# parcels/management/commands/sync_user_wallets.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Sync user wallets with Ganache and ensure proper setup'

    def handle(self, *args, **options):
        User = get_user_model()
        
        for user in User.objects.all():
            if hasattr(user, 'profile'):
                blockchain = BlockchainService(user=user)
                self.stdout.write(f"🔍 Checking user: {user.username}")
                
                if blockchain.account:
                    self.stdout.write(
                        self.style.SUCCESS(f"   ✅ Wallet: {blockchain.account.address}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"   ❌ No wallet configured")
                    )