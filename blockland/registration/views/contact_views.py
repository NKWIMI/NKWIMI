# registration/views/contact_views.py
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages

# Import directly instead of from ..forms
from registration.forms.contact_form import ContactForm

class ContactView(FormView):
    template_name = 'registration/contact.html'
    success_url = reverse_lazy('contact')
    
    def get_form_class(self):
        # Import here to avoid circular imports
        from registration.forms.contact_form import ContactForm
        return ContactForm
    
    def form_valid(self, form):
        form.send_email()
        messages.success(self.request, 'Your message has been sent successfully!')
        return super().form_valid(form)