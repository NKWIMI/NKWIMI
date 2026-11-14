# blockland/views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.defaults import page_not_found, server_error, permission_denied, bad_request

# Error Handlers
def handler400(request, exception):
    return render(request, '400.html', status=400)

def handler403(request, exception):
    return render(request, '403.html', status=403)

def handler404(request, exception):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)

# Core Views
class HomeView(TemplateView):
    template_name = 'core/home.html'

class AboutView(TemplateView):
    template_name = 'core/about.html'

class DocsView(TemplateView):
    template_name = 'core/docs.html'

class APIDocsView(TemplateView):
    template_name = 'core/api_docs.html'

# API Views
class APIStatusView(TemplateView):
    template_name = 'api/status.html'
    extra_context = {'status': 'operational'}