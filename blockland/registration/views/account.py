# registration/views/account.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class AccountOverview(LoginRequiredMixin, TemplateView):
    template_name = 'account/overview.html'

class AccountSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'account/settings.html'