# registration/views/blockchain_views.py
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps

from registration.models import Block, BlockchainTransaction
from registration.services.blockchain_service import BlockchainService

class BlockExplorerView(TemplateView):  # Removed LoginRequiredMixin
    template_name = 'registration/blockchain_templates/block_explorer.html'
    paginate_by = 20  # Reduced for better display

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        search_query = self.request.GET.get('q', '').strip()
        block_hash = self.request.GET.get('block')
        tx_hash = self.request.GET.get('tx')
        block_page = self.request.GET.get('block_page', 1)
        tx_page = self.request.GET.get('tx_page', 1)
        
        # Initialize querysets
        blocks = Block.objects.all().order_by('-height')
        transactions = BlockchainTransaction.objects.select_related('block').order_by('-timestamp')

        # Apply search filters if query exists
        if search_query:
            if search_query.startswith('0x'):
                # Search by hash (block or transaction)
                blocks = blocks.filter(
                    Q(hash__icontains=search_query) | 
                    Q(blockchain_transactions__tx_hash__icontains=search_query)
                ).distinct()
                transactions = transactions.filter(
                    Q(tx_hash__icontains=search_query) |
                    Q(block__hash__icontains=search_query)
                )
            elif search_query.isdigit():
                # Search by block height
                blocks = blocks.filter(height=int(search_query))

        # Separate pagination for blocks and transactions
        block_paginator = Paginator(blocks, self.paginate_by)
        tx_paginator = Paginator(transactions, self.paginate_by)
        
        context.update({
            'blocks': block_paginator.get_page(block_page),
            'transactions': tx_paginator.get_page(tx_page),
            'latest_blocks': Block.objects.order_by('-height')[:5],  # Show last 5 blocks
            'latest_transactions': BlockchainTransaction.objects.select_related('block').order_by('-timestamp')[:5],  # Show last 5 transactions
            'search_query': search_query,
            'block_page_param': 'block_page',
            'tx_page_param': 'tx_page',
        })
        
        # Get single block if specified
        if block_hash:
            context['current_block'] = get_object_or_404(
                Block.objects.prefetch_related('blockchain_transactions'),
                hash=block_hash
            )
        
        # Get single transaction if specified
        if tx_hash:
            context['current_transaction'] = get_object_or_404(
                BlockchainTransaction.objects.select_related('block'),
                tx_hash=tx_hash
            )
        
        return context

class TransactionListView(LoginRequiredMixin, ListView):
    model = BlockchainTransaction
    template_name = 'registration/blockchain_templates/blockchain_transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25
    ordering = ['-timestamp']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('block')
        search_query = self.request.GET.get('q', '').strip()
        
        if search_query:
            if search_query.startswith('0x'):
                # Search by transaction or block hash
                queryset = queryset.filter(
                    Q(tx_hash__icontains=search_query) |
                    Q(block__hash__icontains=search_query)
                )
            elif search_query.isdigit():
                # Search by block height
                queryset = queryset.filter(block__height=search_query)
            else:
                # Search by address (sender or recipient)
                queryset = queryset.filter(
                    Q(sender__icontains=search_query) |
                    Q(recipient__icontains=search_query)
                )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = BlockchainTransaction
    template_name = 'registration/blockchain_templates/transaction_detail.html'
    context_object_name = 'transaction'
    slug_field = 'tx_hash'
    slug_url_kwarg = 'tx_hash'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add related transfer information if available
        try:
            TransferModel = apps.get_model('registration', 'Transfer')
            context['related_transfer'] = TransferModel.objects.filter(
                transaction_hash=self.object.tx_hash
            ).first()
        except Exception:
            context['related_transfer'] = None
        return context

class BlockDetailView(LoginRequiredMixin, DetailView):
    model = Block
    template_name = 'registration/blockchain_templates/block_detail.html'
    context_object_name = 'block'
    
    def get_object(self, queryset=None):
        # Try to get by height first, then by hash
        height = self.kwargs.get('height')
        if height:
            return get_object_or_404(Block, height=height)
        return super().get_object(queryset)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        block = self.get_object()
        
        # Get transactions for this block
        transactions = BlockchainTransaction.objects.filter(block=block).select_related('block')
        context['transactions'] = transactions
        
        # Get previous and next blocks
        context['previous_block'] = Block.objects.filter(height__lt=block.height).order_by('-height').first()
        context['next_block'] = Block.objects.filter(height__gt=block.height).order_by('height').first()
        
        return context

class BlockchainSearchView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/blockchain_templates/blockchain_search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '').strip()
        context['search_query'] = query
        
        if query:
            # Search blocks
            blocks = Block.objects.filter(
                Q(height=query) if query.isdigit() else Q(hash__icontains=query)
            )[:10]
            
            # Search transactions
            transactions = BlockchainTransaction.objects.filter(
                Q(tx_hash__icontains=query) |
                Q(sender__icontains=query) |
                Q(recipient__icontains=query)
            )[:10]
            
            context['blocks'] = blocks
            context['transactions'] = transactions
            context['has_results'] = blocks.exists() or transactions.exists()
        
        return context

class AddressDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/blockchain_templates/address_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        address = self.kwargs.get('address', '').lower()
        context['address'] = address
        
        if address:
            try:
                # Initialize blockchain service
                blockchain_service = BlockchainService()
                
                # Get parcels owned by this address
                parcels = blockchain_service.get_parcels_by_owner(address)
                context['parcels'] = parcels
                
                # Get transactions involving this address
                transactions = BlockchainTransaction.objects.filter(
                    Q(sender__iexact=address) | Q(recipient__iexact=address)
                ).select_related('block').order_by('-timestamp')[:50]
                
                context['transactions'] = transactions
                context['transaction_count'] = transactions.count()
                
                # Calculate balance (sent vs received)
                sent_amount = sum(tx.value for tx in transactions.filter(sender__iexact=address))
                received_amount = sum(tx.value for tx in transactions.filter(recipient__iexact=address))
                context['balance'] = received_amount - sent_amount
                
            except Exception as e:
                context['error'] = str(e)
        
        return context

class BlockchainSyncView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/blockchain_templates/blockchain_sync.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.method == 'POST' and self.request.user.is_staff:
            try:
                blockchain_service = BlockchainService()
                success, message = blockchain_service.sync_all()
                context['sync_result'] = {'success': success, 'message': message}
            except Exception as e:
                context['sync_result'] = {'success': False, 'message': str(e)}
        
        return context
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

class BlockchainStatusView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/blockchain_templates/blockchain_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            blockchain_service = BlockchainService()
            
            # Get blockchain info
            context['chain_id'] = blockchain_service.w3.eth.chain_id
            context['block_number'] = blockchain_service.w3.eth.block_number
            context['gas_price'] = blockchain_service.w3.from_wei(blockchain_service.w3.eth.gas_price, 'gwei')
            context['account_balance'] = blockchain_service.w3.from_wei(
                blockchain_service.w3.eth.get_balance(blockchain_service.account.address), 'ether'
            )
            context['account_address'] = blockchain_service.account.address
            
            # Contract info
            context['contract_address'] = blockchain_service.contract_address
            context['contract_balance'] = blockchain_service.w3.from_wei(
                blockchain_service.w3.eth.get_balance(blockchain_service.contract_address), 'ether'
            )
            
        except Exception as e:
            context['error'] = str(e)
        
        return context