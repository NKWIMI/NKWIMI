from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from registration.models import Parcel, Transfer
from web3 import Web3
import os

class Command(BaseCommand):
    help = 'Diagnose wallet and ownership issues'

    def handle(self, *args, **options):
        User = get_user_model()
        
        self.stdout.write("🔍 Starting wallet diagnosis...")
        
        # Initialize Web3
        try:
            w3 = Web3(Web3.HTTPProvider(os.getenv('WEB3_PROVIDER_URL', 'http://localhost:7545')))
            if not w3.is_connected():
                self.stdout.write(self.style.ERROR('❌ Cannot connect to blockchain node'))
                return
            self.stdout.write("✅ Connected to blockchain node")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Web3 connection error: {str(e)}'))
            return

        # Check all users and their wallets
        self.stdout.write("\n👥 USER WALLETS:")
        for user in User.objects.all():
            if hasattr(user, 'blockchain_address') and user.blockchain_address:
                balance = self.get_balance(w3, user.blockchain_address)
                self.stdout.write(f"  {user.username}: {user.blockchain_address} | Balance: {balance} ETH")
            else:
                self.stdout.write(f"  {user.username}: NO BLOCKCHAIN ADDRESS")

        # Check parcels and their ownership
        self.stdout.write("\n🏠 PARCEL OWNERSHIP:")
        for parcel in Parcel.objects.all():
            parcel_id = parcel.land_id  # Using land_id instead of parcel_id
            
            # Get owner info
            if parcel.owner and hasattr(parcel.owner, 'blockchain_address'):
                django_owner_wallet = parcel.owner.blockchain_address
                django_owner_name = parcel.owner.username
            else:
                django_owner_wallet = "NO OWNER"
                django_owner_name = "NO OWNER"
            
            # Get parcel blockchain owner address
            parcel_owner_wallet = parcel.owner_address if hasattr(parcel, 'owner_address') else "NO OWNER ADDRESS"
            
            status = "✅ MATCH" if django_owner_wallet and parcel_owner_wallet and django_owner_wallet.lower() == parcel_owner_wallet.lower() else "❌ MISMATCH"
            
            self.stdout.write(f"  Parcel {parcel_id}:")
            self.stdout.write(f"    Django Owner: {django_owner_name}")
            self.stdout.write(f"    User Wallet: {django_owner_wallet}")
            self.stdout.write(f"    Parcel Owner Address: {parcel_owner_wallet}")
            self.stdout.write(f"    Status: {status}")

        # Check recent transfers
        self.stdout.write("\n🔄 RECENT TRANSFERS:")
        transfers = Transfer.objects.all().order_by('-created_at')[:5]
        if transfers:
            for transfer in transfers:
                self.stdout.write(f"  Transfer {transfer.id}:")
                self.stdout.write(f"    Parcel: {transfer.parcel.land_id}")
                self.stdout.write(f"    From: {transfer.sender.username if transfer.sender else 'SYSTEM'}")
                self.stdout.write(f"    To: {transfer.recipient.username}")
                self.stdout.write(f"    Status: {transfer.status}")
                self.stdout.write(f"    TX Hash: {transfer.transaction_hash}")
        else:
            self.stdout.write("  No transfers found")

    def get_balance(self, w3, address):
        """Get ETH balance for an address"""
        try:
            balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
            return w3.from_wei(balance_wei, 'ether')
        except:
            return "Error"