from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models import Q
from web3 import Web3
import secrets

class Command(BaseCommand):
    help = 'Generate wallets for users missing blockchain addresses'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        users_without_wallets = User.objects.filter(
            Q(blockchain_address__isnull=True) | 
            Q(blockchain_address='')
        )
        
        self.stdout.write(f"Found {users_without_wallets.count()} users without wallets")
        
        if options['dry_run']:
            self.stdout.write("DRY RUN - No changes will be made")
            for user in users_without_wallets:
                self.stdout.write(f"Would fix: {user.username}")
            return
        
        for user in users_without_wallets:
            private_key = "0x" + secrets.token_hex(32)
            account = Web3().eth.account.from_key(private_key)
            
            user.blockchain_address = account.address
            user.encrypted_private_key = private_key
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Generated wallet for {user.username}: {account.address}')
            )
        
        self.stdout.write(self.style.SUCCESS(f"🎉 Fixed {users_without_wallets.count()} user wallets"))