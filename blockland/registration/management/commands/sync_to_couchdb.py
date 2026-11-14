# registration/management/commands/sync_blockchain_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from registration.models import Transfer, Parcel
from web3 import Web3
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Sync blockchain transfer data with local database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Sync transfers for a specific user only',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Starting blockchain data sync...")
        
        # Initialize Web3
        try:
            w3 = Web3(Web3.HTTPProvider(os.getenv('WEB3_PROVIDER_URL', 'http://localhost:7545')))
            if not w3.is_connected():
                self.stdout.write(
                    self.style.ERROR('❌ Cannot connect to blockchain node')
                )
                return
            self.stdout.write("✅ Connected to blockchain node")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Web3 connection error: {str(e)}')
            )
            return
        
        # Get transfers to sync
        transfers = Transfer.objects.filter(status__in=['pending', 'accepted'])
        
        # Filter by username if specified
        username = options.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
                transfers = transfers.filter(recipient=user)
                self.stdout.write(f"👤 Filtering transfers for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ User {username} not found')
                )
                return
        
        if not transfers.exists():
            self.stdout.write("ℹ️ No transfers found for syncing")
            return
        
        self.stdout.write(f"📋 Found {transfers.count()} transfers to check")
        
        updated_count = 0
        error_count = 0
        
        for transfer in transfers:
            try:
                if not transfer.transaction_hash:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Transfer {transfer.id} has no transaction hash')
                    )
                    continue
                
                self.stdout.write(f"🔍 Checking transfer {transfer.id} with transaction_hash: {transfer.transaction_hash}")
                
                # Check blockchain for transfer status
                try:
                    tx_receipt = w3.eth.get_transaction_receipt(transfer.transaction_hash)
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ Could not get receipt for transaction {transfer.transaction_hash}: {str(e)}')
                    )
                    continue
                
                if tx_receipt:
                    if tx_receipt.status == 1:
                        # Transaction successful on blockchain
                        if transfer.status != 'accepted':
                            transfer.status = 'accepted'
                            transfer.save()
                            
                            # Update parcel ownership if needed
                            parcel = transfer.parcel
                            if parcel.owner != transfer.recipient:
                                parcel.owner = transfer.recipient
                                parcel.save()
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'✅ Updated parcel {parcel.id} ownership to {transfer.recipient.username}'
                                    )
                                )
                            
                            updated_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✅ Updated transfer {transfer.id} status to accepted'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'ℹ️ Transfer {transfer.id} already marked as accepted'
                                )
                            )
                    
                    elif tx_receipt.status == 0:
                        # Transaction failed on blockchain
                        if transfer.status != 'failed':
                            transfer.status = 'failed'
                            transfer.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠️ Marked transfer {transfer.id} as failed (blockchain transaction failed)'
                                )
                            )
                    
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'ℹ️ Transfer {transfer.id} transaction not found on blockchain (may be pending)'
                        )
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing transfer {transfer.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🎉 Sync completed! Updated: {updated_count}, Errors: {error_count}'
            )
        )