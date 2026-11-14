# registration/views/transaction_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q
from ..models import Transaction, User

# Import directly instead of from ..forms
from registration.forms.parcel_forms import ParcelTransferForm

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'registration/transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        # Filter by current user and order by timestamp (not 'date')
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

# Base admin view with authentication check
class AdminBaseView(LoginRequiredMixin):
    login_url = '/admin/login/'
    redirect_field_name = 'redirect_to'

# Admin view for listing all transactions
class AdminViewTransactionsView(AdminBaseView, ListView):
    model = Transaction
    template_name = 'admin/admin_transactions.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        queryset = Transaction.objects.all().order_by('-date')
        
        # Filter by query parameters
        user_id = self.request.GET.get('user')
        if user_id:
            queryset = queryset.filter(user__id=user_id)

        parcel_id = self.request.GET.get('parcel')
        if parcel_id:
            queryset = queryset.filter(parcel__id=parcel_id)

        tx_type = self.request.GET.get('type')
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_transactions'] = self.get_queryset().count()
        context['users'] = User.objects.all()
        return context