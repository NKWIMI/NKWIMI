# registration/views/dashboard_views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import localtime
from web3 import Web3
from registration.models import Transaction, Transfer
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models  # Added missing import

# Connect to blockchain using settings
BLOCKCHAIN_RPC_URL = getattr(settings, 'BLOCKCHAIN_RPC_URL', 'http://127.0.0.1:7545')
w3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC_URL))

User = get_user_model()

class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registration/user_dashboard.html"
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Fetch user profile data
        custom_data = user
        
        # Check if user has a profile with blockchain address
        has_blockchain_profile = (
            hasattr(user, 'profile') and 
            hasattr(user.profile, 'blockchain_address') and 
            user.profile.blockchain_address
        )

        # Blockchain data
        blockchain_connected = w3.is_connected()
        total_blocks = 0
        balance_eth = 0

        if blockchain_connected:
            try:
                # Get total blocks
                total_blocks = w3.eth.block_number
                
                # Get user's ETH balance if they have a blockchain address
                if has_blockchain_profile:
                    user_address = user.profile.blockchain_address
                    if w3.is_address(user_address):
                        balance_wei = w3.eth.get_balance(user_address)
                        balance_eth = w3.from_wei(balance_wei, 'ether')
            except Exception as e:
                print(f"Error fetching blockchain data: {e}")
                blockchain_connected = False

        # User transactions from database
        try:
            user_transactions_qs = Transaction.objects.filter(user=user).order_by('-date')
            user_transactions_count = user_transactions_qs.count()
            recent_transactions = user_transactions_qs[:5]  # Show only 5 recent transactions
        except Exception as e:
            print(f"Error fetching user transactions: {e}")
            user_transactions_count = 0
            recent_transactions = []

        # User transfer history
        try:
            # Get transfers where user is either sender or recipient
            user_transfers = Transfer.objects.filter(
                models.Q(sender=user) | models.Q(recipient=user)
            ).order_by('-created_at')
            user_transfers_count = user_transfers.count()
            recent_transfers = user_transfers[:5]  # Show only 5 recent transfers
        except Exception as e:
            print(f"Error fetching user transfers: {e}")
            user_transfers_count = 0
            recent_transfers = []

        # Last login
        last_login = localtime(user.last_login) if user.last_login else None

        context.update({
            'user': user,
            'custom_data': custom_data,
            'total_blocks': total_blocks,
            'user_transactions_count': user_transactions_count,
            'recent_transactions': recent_transactions,
            'user_transfers_count': user_transfers_count,
            'recent_transfers': recent_transfers,
            'last_login': last_login,
            'balance_eth': balance_eth,
            'blockchain_connected': blockchain_connected,
            'blockchain_rpc_url': BLOCKCHAIN_RPC_URL,
            'has_blockchain_profile': has_blockchain_profile,
        })

        return context


# Optional: Admin dashboard view
class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "registration/admin_dashboard.html"
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add admin-specific context data here
        from registration.models import User, Parcel, Transfer
        total_users = User.objects.count()
        total_parcels = Parcel.objects.count()
        total_transfers = Transfer.objects.count()
        pending_transfers = Transfer.objects.filter(status='pending').count()
        
        context.update({
            'user': user,
            'is_admin': True,
            'total_users': total_users,
            'total_parcels': total_parcels,
            'total_transfers': total_transfers,
            'pending_transfers': pending_transfers,
        })
        
        return context