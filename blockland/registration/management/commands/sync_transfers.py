# management/commands/sync_transfers.py
from django.core.management.base import BaseCommand
from registration.models import Transfer
from registration.views.transfer_views import sync_transfer_with_blockchain

class Command(BaseCommand):
    help = 'Sync all transfers with blockchain state'

    def handle(self, *args, **options):
        transfers = Transfer.objects.filter(status=Transfer.PENDING)
        self.stdout.write(f"Syncing {transfers.count()} pending transfers...")
        
        for transfer in transfers:
            result = sync_transfer_with_blockchain(transfer)
            self.stdout.write(f"Transfer {transfer.id}: {result}")