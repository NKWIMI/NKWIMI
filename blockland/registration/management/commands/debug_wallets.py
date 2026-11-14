# management/commands/debug_wallets.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from web3 import Web3

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug wallet states and balances'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Wallet Debug Information")
        self.stdout.write("=" * 50)
        
        w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
        
        if not w3.is_connected():
            self.stdout.write("❌ Cannot connect to Ethereum node")
            return
        
        # System wallet
        system_addr = '0xee7807d939c67a695a7958D3f23558DB27d0b11b'
        system_balance = w3.eth.get_balance(system_addr)
        self.stdout.write(f"\n💼 System Wallet: {system_addr}")
        self.stdout.write(f"   Balance: {w3.from_wei(system_balance, 'ether')} ETH")
        
        # User wallets from your logs
        user_wallets = [
            ('user3', '0x70997970C51812dc3A010C7d01b50e0d17dc79C8'),
            ('user4', '0x6Fa815A63B6808cd8b36f4059D8DABE3BB53D0F9'),
            ('user5', '0x4b84dc4bA8CC54f025d4cd285F3BA8Dc5cFE2D34'),
            ('user6', '0x1401490470Dd33eAb445EA221b764719Ae2A9c96'),
            ('admin', '0x5eb22CcA0610065f40921f5288e18bfD49b04167'),
        ]
        
        self.stdout.write(f"\n👥 User Wallets:")
        for username, address in user_wallets:
            balance = w3.eth.get_balance(address)
            balance_eth = w3.from_wei(balance, 'ether')
            
            # Check if user exists in database
            try:
                user = User.objects.get(username=username)
                has_profile = hasattr(user, 'profile')
                has_private_key = has_profile and hasattr(user.profile, 'encrypted_private_key') and user.profile.encrypted_private_key
                
                self.stdout.write(f"\n👤 {username}:")
                self.stdout.write(f"   Address: {address}")
                self.stdout.write(f"   Balance: {balance_eth} ETH")
                self.stdout.write(f"   Has Profile: {has_profile}")
                self.stdout.write(f"   Has Private Key: {has_private_key}")
                
                if has_profile:
                    self.stdout.write(f"   DB Address: {user.profile.blockchain_address}")
                    
            except User.DoesNotExist:
                self.stdout.write(f"\n👤 {username}: ❌ User not in database")
                self.stdout.write(f"   Address: {address}")
                self.stdout.write(f"   Balance: {balance_eth} ETH")
        
        # Check all Ganache accounts
        self.stdout.write(f"\n📋 All Ganache Accounts:")
        for i, account in enumerate(w3.eth.accounts):
            balance = w3.eth.get_balance(account)
            balance_eth = w3.from_wei(balance, 'ether')
            self.stdout.write(f"   {i}: {account} - {balance_eth} ETH")