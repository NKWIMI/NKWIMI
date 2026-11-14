from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from registration.models import Parcel

class Command(BaseCommand):
    help = 'Fix parcel ownership mismatches between User and Parcel models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--parcel',
            type=str,
            help='Fix specific parcel only',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        
        self.stdout.write("🔧 Fixing ownership mismatches...")
        
        parcels = Parcel.objects.all()
        if options['parcel']:
            parcels = parcels.filter(land_id=options['parcel'])
        
        fixed_count = 0
        
        for parcel in parcels:
            if parcel.owner and hasattr(parcel.owner, 'blockchain_address'):
                user_wallet = parcel.owner.blockchain_address
                parcel_wallet = parcel.owner_address
                
                if user_wallet and parcel_wallet and user_wallet.lower() != parcel_wallet.lower():
                    self.stdout.write(f"⚠️ Fixing {parcel.land_id}:")
                    self.stdout.write(f"   Parcel owner_address: {parcel_wallet}")
                    self.stdout.write(f"   User blockchain_address: {user_wallet}")
                    
                    # Update parcel owner_address to match user's blockchain_address
                    parcel.owner_address = user_wallet
                    parcel.save()
                    
                    self.stdout.write(f"✅ Updated {parcel.land_id} owner_address to {user_wallet}")
                    fixed_count += 1
                else:
                    self.stdout.write(f"✅ {parcel.land_id}: Ownership correct")
            else:
                self.stdout.write(f"⚠️ {parcel.land_id}: No owner or blockchain address")
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Fixed {fixed_count} ownership mismatches"))