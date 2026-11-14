from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, UpdateView,TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from registration.models.user_models import User
from registration.forms import UserForm, UserUpdateForm

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"

class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'registration/profile_detail.html'
    context_object_name = 'profile_user'

    def get_object(self):
        return self.request.user

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'registration/profile_form.html'
    success_url = reverse_lazy('profile:profile_detail')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)

class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'registration/user_form.html'
    success_url = reverse_lazy('profile:profile_detail')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Account information updated successfully!')
        return super().form_valid(form)
