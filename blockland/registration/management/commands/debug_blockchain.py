# parcels/management/commands/debug_blockchain.py
from django.core.management.base import BaseCommand
from web3 import Web3
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Debug blockchain connection and registration issues'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Blockchain Debug Information")
        self.stdout.write("=" * 50)
        
        # Check if blockchain service exists
        try:
            from blockchain.service import BlockchainService
            blockchain = BlockchainService()
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"❌ Cannot import BlockchainService: {e}"))
            self.stdout.write("💡 Make sure blockchain/service.py exists in your project")
            return

        # Check Web3 connection
        if blockchain.w3:
            self.stdout.write(self.style.SUCCESS("✅ Web3 Connected"))
            self.stdout.write(f"   Chain ID: {blockchain.w3.eth.chain_id}")
            self.stdout.write(f"   Latest Block: {blockchain.w3.eth.block_number}")
            self.stdout.write(f"   Gas Price: {blockchain.w3.eth.gas_price}")
        else:
            self.stdout.write(self.style.ERROR("❌ Web3 Not Connected"))
            return

        # Check account
        if blockchain.account:
            self.stdout.write(self.style.SUCCESS("✅ Account Configured"))
            self.stdout.write(f"   Address: {blockchain.account.address}")
            balance = blockchain.w3.eth.get_balance(blockchain.account.address)
            self.stdout.write(f"   Balance: {blockchain.w3.from_wei(balance, 'ether')} ETH")
        else:
            self.stdout.write(self.style.ERROR("❌ No Account Available"))
            return

        # Check contract
        if blockchain.contract:
            self.stdout.write(self.style.SUCCESS("✅ Contract Configured"))
            self.stdout.write(f"   Address: {blockchain.contract_address}")
            
            # Check contract code
            code = blockchain.w3.eth.get_code(blockchain.contract_address)
            if code == b'':
                self.stdout.write(self.style.ERROR("❌ No code at contract address"))
            else:
                self.stdout.write(f"   Contract has code: {len(code)} bytes")
        else:
            self.stdout.write(self.style.ERROR("❌ Contract Not Configured"))

        self.stdout.write("\n✅ Debug completed")