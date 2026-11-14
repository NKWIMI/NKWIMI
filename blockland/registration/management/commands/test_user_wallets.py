# registration/management/commands/test_user_wallets.py
from django.core.management.base import BaseCommand
from registration.models import User
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Test user wallet functionality'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing User Wallets")
        self.stdout.write("=" * 40)
        
        # Test with specific users
        test_users = ['user3', 'user4', 'user5', 'user6', 'admin']
        
        for username in test_users:
            try:
                user = User.objects.get(username=username)
                self.stdout.write(f"\n👤 Testing user: {username}")
                self.stdout.write(f"   Address: {user.blockchain_address}")
                self.stdout.write(f"   Has Private Key: {bool(user.encrypted_private_key)}")
                
                # Test blockchain service with user
                blockchain = BlockchainService(user=user)
                if blockchain.account:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Blockchain Account: {blockchain.account.address}"))
                    
                    # Check balance
                    balance = blockchain.w3.eth.get_balance(blockchain.account.address)
                    balance_eth = blockchain.w3.from_wei(balance, 'ether')
                    self.stdout.write(f"   💰 Balance: {balance_eth} ETH")
                else:
                    self.stdout.write(self.style.ERROR("   ❌ No blockchain account"))
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"   ⚠ User {username} not found"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error: {e}"))
        
        self.stdout.write("\n✅ User wallet test completed")