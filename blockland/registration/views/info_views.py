from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class BlockchainInfoView(TemplateView):
    """
    View for displaying blockchain information and educational content
    Accessible to all users (including non-authenticated)
    """
    template_name = 'registration/blockchain_templates/blockchain_info.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context data here if needed
        context['page_title'] = 'Blockchain Information - Blockland'
        return context


class HowItWorksView(TemplateView):
    """
    View for displaying how the platform works
    """
    template_name = 'registration/how_it_works.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'How It Works - Blockland'
        return context


class FAQView(TemplateView):
    """
    View for Frequently Asked Questions
    """
    template_name = 'registration/faq.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'FAQ - Blockland'
        return context