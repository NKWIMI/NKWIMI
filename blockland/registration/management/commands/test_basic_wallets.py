# management/commands/test_basic_wallets.py
import os
import sys
from django.core.management.base import BaseCommand
from web3 import Web3

class Command(BaseCommand):
    help = 'Basic wallet connectivity test'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Basic Wallet Connectivity Test")
        self.stdout.write("=" * 50)
        
        # Import BlockchainService safely
        try:
            # Method 1: Direct import from root
            from blockchain_service import BlockchainService
        except ImportError:
            try:
                # Method 2: Check if it's in registration app
                from registration.blockchain_service import BlockchainService
            except ImportError:
                self.stdout.write("❌ Could not import BlockchainService")
                self.stdout.write("💡 Make sure blockchain_service.py is in your project root or registration app")
                return
        
        # Test 1: Direct Web3 connection
        self.stdout.write("\n🌐 TEST 1: Direct Web3 Connection")
        w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
        
        if w3.is_connected():
            self.stdout.write("✅ Connected to Ethereum node")
            self.stdout.write(f"   Chain ID: {w3.eth.chain_id}")
            self.stdout.write(f"   Block Number: {w3.eth.block_number}")
        else:
            self.stdout.write("❌ Failed to connect to Ethereum node")
            return
        
        # Test 2: BlockchainService initialization
        self.stdout.write("\n🔄 TEST 2: BlockchainService Initialization")
        try:
            blockchain = BlockchainService()
            
            if blockchain.w3 and blockchain.w3.is_connected():
                self.stdout.write("✅ BlockchainService connected successfully")
                self.stdout.write(f"   Current account: {blockchain.account.address if blockchain.account else 'None'}")
            else:
                self.stdout.write("❌ BlockchainService failed to connect")
                
        except Exception as e:
            self.stdout.write(f"❌ BlockchainService initialization failed: {e}")
        
        self.stdout.write("\n✅ Basic test completed!")