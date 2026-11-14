# registration/management/commands/check_blockchain_state.py
from django.core.management.base import BaseCommand
from registration.models import Parcel
from registration.services.blockchain_service import BlockchainService

class Command(BaseCommand):
    help = 'Check current blockchain state and parcel ownership'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Blockchain State Check")
        self.stdout.write("=" * 40)
        
        blockchain = BlockchainService()  # System wallet for checking
        
        # Check some key parcels
        test_parcels = ['LOT05', 'LOT04', 'LOT03', 'LAND01']
        
        for parcel_id in test_parcels:
            try:
                parcel_data = blockchain.get_parcel(parcel_id)
                if parcel_data and parcel_data.get('exists'):
                    self.stdout.write(f"\n🏠 Parcel: {parcel_id}")
                    self.stdout.write(f"   Owner: {parcel_data['owner']}")
                    self.stdout.write(f"   Frozen: {parcel_data.get('frozen', False)}")
                    self.stdout.write(f"   Latest IPFS Hash: {parcel_data.get('latest_ipfs_hash', 'None')}")
                else:
                    self.stdout.write(f"\n🏠 Parcel: {parcel_id} - Not found on blockchain")
            except Exception as e:
                self.stdout.write(f"\n🏠 Parcel: {parcel_id} - Error: {e}")
        
        self.stdout.write("\n✅ Blockchain state check completed")