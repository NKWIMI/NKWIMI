# parcels/management/commands/debug_parcels.py
from django.core.management.base import BaseCommand
from registration.models import Parcel
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Debug parcel ownership and blockchain status'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Parcel Ownership Debug")
        self.stdout.write("=" * 50)
        
        parcels = Parcel.objects.all()
        
        if not parcels:
            self.stdout.write(self.style.WARNING("❌ No parcels found in database"))
            return
            
        blockchain = BlockchainService()  # System wallet for checking
        
        for parcel in parcels:
            self.stdout.write(f"\n🏠 Parcel: {parcel.land_id} (ID: {parcel.id})")
            self.stdout.write(f"   Django Owner: {parcel.owner.username}")
            
            if hasattr(parcel.owner, 'profile'):
                profile = parcel.owner.profile
                self.stdout.write(f"   Owner Address: {profile.blockchain_address}")
                self.stdout.write(f"   Has Private Key: {bool(profile.encrypted_private_key)}")
            else:
                self.stdout.write(self.style.WARNING("   ⚠ Owner has no profile"))
                
            # Check blockchain status
            blockchain_data = blockchain.get_parcel(parcel.land_id)
            if blockchain_data and blockchain_data.get('exists'):
                self.stdout.write(self.style.SUCCESS("   ✅ Registered on Blockchain"))
                self.stdout.write(f"   Blockchain Owner: {blockchain_data['owner']}")
                
                # Check ownership match
                if hasattr(parcel.owner, 'profile') and parcel.owner.profile.blockchain_address:
                    django_owner = parcel.owner.profile.blockchain_address.lower()
                    blockchain_owner = blockchain_data