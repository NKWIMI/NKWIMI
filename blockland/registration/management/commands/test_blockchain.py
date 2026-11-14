# parcels/management/commands/test_blockchain.py
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Test basic blockchain setup'

    def handle(self, *args, **options):
        self.stdout.write("🧪 Testing Blockchain Setup")
        self.stdout.write("=" * 40)
        
        # Check settings
        blockchain_config = getattr(settings, "BLOCKCHAIN_CONFIG", {})
        
        self.stdout.write("📋 Configuration Check:")
        self.stdout.write(f"   GANACHE_URL: {blockchain_config.get('GANACHE_URL', 'Not set')}")
        self.stdout.write(f"   CONTRACT_ADDRESS: {blockchain_config.get('CONTRACT_ADDRESS', 'Not set')}")
        self.stdout.write(f"   CONTRACT_ABI_PATH: {blockchain_config.get('CONTRACT_ABI_PATH', 'Not set')}")
        
        if blockchain_config.get('CONTRACT_ABI_PATH'):
            abi_path = blockchain_config['CONTRACT_ABI_PATH']
            if os.path.exists(abi_path):
                self.stdout.write(self.style.SUCCESS("   ✅ ABI file exists"))
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ ABI file not found: {abi_path}"))
        
        # Try to import and initialize blockchain service
        try:
            from blockchain.service import BlockchainService
            self.stdout.write(self.style.SUCCESS("✅ BlockchainService imported successfully"))
            
            # Test initialization
            blockchain = BlockchainService()
            self.stdout.write(self.style.SUCCESS("✅ BlockchainService initialized"))
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"❌ Cannot import BlockchainService: {e}"))
            self.stdout.write("💡 Make sure you have a blockchain/service.py file")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error initializing BlockchainService: {e}"))