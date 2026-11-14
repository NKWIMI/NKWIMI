# management/commands/test_transfer.py (UPDATED)
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blockchain_service import BlockchainService

User = get_user_model()

class Command(BaseCommand):
    help = 'Test parcel transfer with proper wallet switching'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Parcel Transfer with Wallet Switching")
        self.stdout.write("=" * 60)
        
        blockchain = BlockchainService()
        
        # Test parcels from your logs with their owners
        test_parcels = [
            {'id': 'LOT05', 'owner': '0x1401490470Dd33eAb445EA221b764719Ae2A9c96', 'username': 'user6'},
            {'id': 'LOT04', 'owner': '0x4b84dc4bA8CC54f025d4cd285F3BA8Dc5cFE2D34', 'username': 'user5'},
            {'id': 'LOT03', 'owner': '0x6Fa815A63B6808cd8b36f4059D8DABE3BB53D0F9', 'username': 'user4'},
            {'id': 'LOT01', 'owner': '0x70997970C51812dc3A010C7d01b50e0d17dc79C8', 'username': 'user3'},
        ]
        
        success_count = 0
        total_count = len(test_parcels)
        
        for parcel in test_parcels:
            self.stdout.write(f"\n🏠 Testing with parcel: {parcel['id']}")
            self.stdout.write(f"   Owner: {parcel['username']}")
            self.stdout.write(f"   Owner Address: {parcel['owner']}")
            
            # Get blockchain owner for verification
            parcel_data = blockchain.get_parcel(parcel['id'])
            if parcel_data:
                blockchain_owner = parcel_data.get('owner', 'Unknown')
                self.stdout.write(f"   Blockchain Owner: {blockchain_owner}")
            else:
                self.stdout.write(f"   ❌ Could not fetch parcel from blockchain")
                continue
            
            # SWITCH TO THE CORRECT WALLET
            self.stdout.write(f"   🔄 Switching to owner wallet...")
            
            if blockchain.switch_to_specific_address(parcel['owner']):
                self.stdout.write(f"   ✅ Switched to: {blockchain.account.address}")
                
                # Now test ownership validation
                self.stdout.write(f"   🔍 Validating ownership...")
                
                if blockchain.validate_ownership(parcel['id'], parcel['owner']):
                    self.stdout.write(f"   ✅ Ownership validation PASSED")
                    success_count += 1
                    
                    # Test transfer initiation (just gas estimation, not actual transfer)
                    try:
                        test_recipient = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"  # user3 as test recipient
                        function_call = blockchain.contract.functions.initiateTransfer(
                            parcel['id'], 
                            test_recipient, 
                            "test_document_hash"
                        )
                        
                        gas_estimate = function_call.estimate_gas({
                            'from': blockchain.account.address
                        })
                        
                        self.stdout.write(f"   ✅ Transfer setup successful (Gas: {gas_estimate})")
                        
                    except Exception as e:
                        self.stdout.write(f"   ⚠ Transfer setup failed: {e}")
                        
                else:
                    self.stdout.write(f"   ❌ Ownership validation FAILED")
            else:
                self.stdout.write(f"   ❌ Failed to switch to owner wallet")
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"📊 TEST SUMMARY:")
        self.stdout.write(f"   Total parcels tested: {total_count}")
        self.stdout.write(f"   Successful validations: {success_count}")
        self.stdout.write(f"   Success rate: {(success_count/total_count)*100:.1f}%")
        
        if success_count == total_count:
            self.stdout.write("🎉 ALL TESTS PASSED! Wallet switching is working correctly.")
        else:
            self.stdout.write("❌ Some tests failed. Check the logs above.")