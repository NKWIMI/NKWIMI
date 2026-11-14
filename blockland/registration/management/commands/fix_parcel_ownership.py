# registration/management/commands/fix_parcel_ownership.py
from django.core.management.base import BaseCommand
from registration.models import Parcel
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Fix parcel ownership on blockchain'

    def handle(self, *args, **options):
        self.stdout.write("🔧 Fixing Parcel Ownership on Blockchain")
        self.stdout.write("=" * 50)
        
        parcels = Parcel.objects.all()
        
        for parcel in parcels:
            self.stdout.write(f"\n🏠 Processing parcel: {parcel.land_id}")
            self.stdout.write(f"   Django Owner: {parcel.owner.username}")
            
            if not hasattr(parcel.owner, 'blockchain_address') or not parcel.owner.blockchain_address:
                self.stdout.write(self.style.WARNING("   ⚠ Owner has no wallet"))
                continue
                
            owner_address = parcel.owner.blockchain_address
            self.stdout.write(f"   Owner Address: {owner_address}")
            
            blockchain = BlockchainService(user=parcel.owner)
            blockchain_data = blockchain.get_parcel(parcel.land_id)
            
            if blockchain_data and blockchain_data.get('exists'):
                blockchain_owner = blockchain_data['owner']
                self.stdout.write(f"   Current Blockchain Owner: {blockchain_owner}")
                
                if blockchain_owner.lower() == owner_address.lower():
                    self.stdout.write(self.style.SUCCESS("   ✅ Ownership already correct"))
                elif blockchain_owner == "0x0000000000000000000000000000000000000000":
                    self.stdout.write(self.style.WARNING("   ⚡ Parcel has zero address owner - needs re-registration"))
                    
                    # Try to re-register with correct owner
                    try:
                        self.stdout.write("   🚀 Re-registering parcel with correct owner...")
                        tx_hash = blockchain.register_parcel(
                            parcel.land_id,
                            owner_address,
                            parcel.latest_ipfs_hash or "fixed_ownership_hash"
                        )
                        if tx_hash:
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Re-registered: {tx_hash}"))
                        else:
                            self.stdout.write(self.style.ERROR("   ❌ Re-registration failed"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Re-registration error: {e}"))
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ Ownership mismatch - parcel owned by different address"))
            else:
                self.stdout.write(self.style.WARNING("   ⚠ Parcel not found on blockchain"))
        
        self.stdout.write("\n✅ Ownership fix completed")