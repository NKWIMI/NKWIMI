# registration/management/commands/fund_users.py
from django.core.management.base import BaseCommand
from registration.models import User
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Fund user wallets with ETH'

    def handle(self, *args, **options):
        self.stdout.write("💰 Funding User Wallets")
        self.stdout.write("=" * 40)
        
        # Users to fund
        users_to_fund = ['user3', 'user4', 'user5', 'user6']
        
        for username in users_to_fund:
            try:
                user = User.objects.get(username=username)
                blockchain = BlockchainService(user=user)
                
                if blockchain.account:
                    # Check current balance
                    balance = blockchain.w3.eth.get_balance(blockchain.account.address)
                    balance_eth = blockchain.w3.from_wei(balance, 'ether')
                    
                    self.stdout.write(f"\n👤 User: {username}")
                    self.stdout.write(f"   Address: {blockchain.account.address}")
                    self.stdout.write(f"   Current Balance: {balance_eth} ETH")
                    
                    if balance_eth < 1.0:  # Fund if less than 1 ETH
                        success = blockchain.fund_user_account(blockchain.account.address, 2.0)
                        if success:
                            self.stdout.write(self.style.SUCCESS("   ✅ Funded with 2 ETH"))
                        else:
                            self.stdout.write(self.style.ERROR("   ❌ Funding failed"))
                    else:
                        self.stdout.write("   ✅ Sufficient balance")
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error funding {username}: {e}"))
        
        self.stdout.write("\n✅ User funding completed")