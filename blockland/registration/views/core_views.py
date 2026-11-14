# registration/views/core_views.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from ..models import PropertyParcel, PendingTransfer, User, AuditLog

class HomeView(TemplateView):
    template_name = 'registration/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['parcels'] = PropertyParcel.objects.filter(
                owner=self.request.user
            ).select_related('owner')[:5]
        return context

class AboutView(TemplateView):
    template_name = 'core/about.html'

class ContactView(TemplateView):
    template_name = 'core/contact.html'

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'registration/admin_dashboard.html'
    login_url = '/login/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_count'] = User.objects.count()
        context['parcel_count'] = PropertyParcel.objects.count()
        context['pending_transfers'] = PendingTransfer.objects.filter(active=True).count()
        return context

class UserDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/dashboard.html'
    login_url = '/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'page_title': 'User Dashboard - Blockland',
            'user_parcels': PropertyParcel.objects.filter(owner=user.profile)[:5] if hasattr(user, 'profile') else [],
            'recent_transfers': PendingTransfer.objects.filter(
                Q(sender=user) | Q(recipient=user)
            ).order_by('-timestamp')[:5],
            'user_activity': AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
        })
        return context

class DocumentationView(LoginRequiredMixin, TemplateView):
    template_name = 'core/docs.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Documentation'
        return context

class AIDocumentationView(LoginRequiredMixin, TemplateView):
    template_name = 'core/ai_doc.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'AI Documentation'
        context['ai_features'] = [
            'Smart contract analysis',
            'Blockchain data interpretation',
            'Transaction pattern recognition',
            'Document verification assistance',
            'Property history insights'
        ]
        return context

class APIDocumentationView(LoginRequiredMixin, TemplateView):
    template_name = 'core/api_doc.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'API Documentation'
        context['api_endpoints'] = [
            {'endpoint': '/api/status/', 'method': 'GET', 'description': 'Check API status and server health'},
            {'endpoint': '/api/auth/', 'method': 'POST', 'description': 'Authentication endpoint for user login'},
            {'endpoint': '/api/auth/register/', 'method': 'POST', 'description': 'User registration endpoint'},
            {'endpoint': '/api/properties/', 'method': 'GET', 'description': 'List all property parcels'},
            {'endpoint': '/api/properties/{id}/', 'method': 'GET', 'description': 'Get specific property details'},
            {'endpoint': '/api/properties/create/', 'method': 'POST', 'description': 'Create new property parcel'},
            {'endpoint': '/api/blockchain/explorer/', 'method': 'GET', 'description': 'Blockchain data explorer'},
            {'endpoint': '/api/transactions/', 'method': 'GET', 'description': 'List blockchain transactions'},
            {'endpoint': '/api/users/profile/', 'method': 'GET', 'description': 'Get user profile information'},
            {'endpoint': '/api/users/profile/update/', 'method': 'PUT', 'description': 'Update user profile'},
        ]
        context['example_request'] = """fetch('/api/status/')
  .then(response => response.json())
  .then(data => console.log(data));"""
        return context