# management/commands/test_wallet_switching.py
import os
import sys
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from blockchain_service import BlockchainService
except ImportError:
    try:
        from registration.blockchain_service import BlockchainService
    except ImportError:
        from .blockchain_service import BlockchainService

User = get_user_model()

class Command(BaseCommand):
    help = 'Test wallet switching functionality'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Wallet Switching")
        self.stdout.write("=" * 50)
        
        blockchain = BlockchainService()
        
        # Test switching to specific addresses from Ganache
        test_addresses = [
            ('Ganache Account 1', '0x5F5430e362ba90c30a845eDB8f3A96338b9447aF'),
            ('Ganache Account 2', '0xe7930d3557D21242fC7645Ca4155CB3F10ffF291'),
            ('Ganache Account 3', '0x0b9A2F1191eC6351770Ff671A07592dEF2D043Ad'),
            ('Ganache Account 4', '0x29435e68b75DBafB9fCe21B6Fc50E31cD7275b7B'),
        ]
        
        # Test 1: Switch to Ganache addresses
        self.stdout.write("\n🔑 TEST 1: Switching to Ganache addresses")
        self.stdout.write("-" * 40)
        
        for name, address in test_addresses:
            self.stdout.write(f"\n👤 Testing: {name}")
            self.stdout.write(f"   Address: {address}")
            
            if blockchain.switch_to_specific_address(address):
                self.stdout.write(f"   ✅ Successfully switched to: {blockchain.account.address}")
                
                # Check balance
                balance = blockchain.w3.eth.get_balance(blockchain.account.address)
                balance_eth = blockchain.w3.from_wei(balance, 'ether')
                self.stdout.write(f"   💰 Balance: {balance_eth} ETH")
            else:
                self.stdout.write(f"   ❌ Failed to switch to address: {address}")
        
        self.stdout.write("\n✅ Wallet switching test completed!")