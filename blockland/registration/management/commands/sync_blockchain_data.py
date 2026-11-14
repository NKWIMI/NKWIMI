# registration/management/commands/sync_blockchain_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from registration.models import Transfer, Parcel
from web3 import Web3
from web3.exceptions import TransactionNotFound
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
        parser.add_argument(
            '--min-confirmations',
            type=int,
            default=1,
            help='Minimum block confirmations required (default: 1)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 Starting blockchain data sync...")
        
        # Initialize Web3
        w3 = self.setup_web3()
        if not w3:
            return
        
        # Get transfers to sync
        transfers = self.get_transfers_to_sync(options.get('username'))
        if not transfers:
            return
        
        self.sync_transfers(w3, transfers, options.get('min_confirmations', 1))
    
    def setup_web3(self):
        """Initialize and validate Web3 connection"""
        try:
            provider_url = os.getenv('WEB3_PROVIDER_URL', 'http://localhost:7545')
            w3 = Web3(Web3.HTTPProvider(provider_url))
            
            if not w3.is_connected():
                self.stdout.write(self.style.ERROR('❌ Cannot connect to blockchain node'))
                return None
            
            self.stdout.write(f"✅ Connected to blockchain node (Chain ID: {w3.eth.chain_id})")
            return w3
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Web3 connection error: {str(e)}'))
            return None
    
    def get_transfers_to_sync(self, username=None):
        """Get transfers that need syncing"""
        transfers = Transfer.objects.filter(status__in=['pending', 'accepted'])
        
        if username:
            try:
                user = User.objects.get(username=username)
                transfers = transfers.filter(recipient=user)
                self.stdout.write(f"👤 Filtering transfers for user: {username}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ User {username} not found'))
                return None
        
        transfer_count = transfers.count()
        if transfer_count == 0:
            self.stdout.write("ℹ️ No transfers found for syncing")
            return None
        
        self.stdout.write(f"📋 Found {transfer_count} transfers to check")
        return transfers
    
    def sync_transfers(self, w3, transfers, min_confirmations):
        """Sync transfer status with blockchain"""
        updated_count = 0
        error_count = 0
        
        for transfer in transfers:
            try:
                result = self.process_transfer(w3, transfer, min_confirmations)
                if result == 'updated':
                    updated_count += 1
                elif result == 'error':
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'❌ Error processing transfer {transfer.id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'🎉 Sync completed! Updated: {updated_count}, Errors: {error_count}'))
    
    def process_transfer(self, w3, transfer, min_confirmations):
        """Process a single transfer"""
        # Validate transaction hash
        if not transfer.transaction_hash:
            self.stdout.write(self.style.WARNING(f'⚠️ Transfer {transfer.id} has no transaction hash'))
            return 'error'
        
        # Clean and validate transaction hash
        tx_hash = transfer.transaction_hash.strip()
        if not tx_hash.startswith('0x'):
            tx_hash = '0x' + tx_hash
        
        self.stdout.write(f"🔍 Checking transfer {transfer.id} with tx: {tx_hash}")
        
        try:
            # Get transaction receipt
            tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            self.stdout.write(self.style.WARNING(f'ℹ️ Transfer {transfer.id} transaction not found on blockchain (may be pending)'))
            return 'pending'
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Could not get receipt for transaction {tx_hash}: {str(e)}'))
            return 'error'
        
        # Check confirmations
        current_block = w3.eth.block_number
        confirmations = current_block - tx_receipt.blockNumber
        
        if confirmations < min_confirmations:
            self.stdout.write(self.style.WARNING(f'ℹ️ Transfer {transfer.id} has {confirmations}/{min_confirmations} confirmations'))
            return 'pending'
        
        # Process based on transaction status
        if tx_receipt.status == 1:  # Success
            return self.handle_successful_transfer(transfer)
        else:  # Failed
            return self.handle_failed_transfer(transfer)
    
    def handle_successful_transfer(self, transfer):
        """Handle successful blockchain transaction"""
        if transfer.status != 'accepted':
            transfer.status = 'accepted'
            transfer.save()
            
            # Update parcel ownership
            parcel = transfer.parcel
            if parcel.owner != transfer.recipient:
                old_owner = parcel.owner.username if parcel.owner else 'None'
                new_owner = transfer.recipient.username
                parcel.owner = transfer.recipient
                parcel.save()
                
                self.stdout.write(self.style.SUCCESS(f'✅ Updated parcel {parcel.id} ownership: {old_owner} → {new_owner}'))
            
            self.stdout.write(self.style.SUCCESS(f'✅ Updated transfer {transfer.id} status to accepted'))
            return 'updated'
        else:
            self.stdout.write(self.style.WARNING(f'ℹ️ Transfer {transfer.id} already accepted'))
            return 'no_change'
    
    def handle_failed_transfer(self, transfer):
        """Handle failed blockchain transaction"""
        if transfer.status != 'failed':
            transfer.status = 'failed'
            transfer.save()
            self.stdout.write(self.style.WARNING(f'⚠️ Marked transfer {transfer.id} as failed (blockchain transaction failed)'))
            return 'updated'
        else:
            self.stdout.write(self.style.WARNING(f'ℹ️ Transfer {transfer.id} already marked as failed'))
            return 'no_change'